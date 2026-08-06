"""Files connector: CSV and Parquet on local disk or S3, via pyarrow.

One implementation, two schemes — `file:///path/to/dir` and
`s3://bucket/prefix` — resolved by `pyarrow.fs.FileSystem.from_uri`, so S3
needs no extra SDK and credentials come from the standard AWS environment.

Native names are file paths relative to the base URI (e.g. `sales/customers.csv`).
v0.1 reads whole files and filters in memory — fine for typical onboarded
datasets; predicate/column pushdown is a planned optimization.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from tabella_core.connectors import Connector, FetchResult, register
from tabella_core.models import AssetDescriptor, AssetSchema, FieldDef, FieldType

_EXTENSIONS = (".csv", ".parquet")


def canonical_type(arrow_type: Any) -> FieldType:
    import pyarrow as pa

    if pa.types.is_boolean(arrow_type):
        return FieldType.boolean
    if pa.types.is_integer(arrow_type):
        return FieldType.integer
    if pa.types.is_floating(arrow_type) or pa.types.is_decimal(arrow_type):
        return FieldType.number
    if pa.types.is_string(arrow_type) or pa.types.is_large_string(arrow_type):
        return FieldType.string
    if pa.types.is_timestamp(arrow_type):
        return FieldType.datetime
    if pa.types.is_date(arrow_type):
        return FieldType.date
    if pa.types.is_binary(arrow_type) or pa.types.is_large_binary(arrow_type):
        return FieldType.binary
    if (
        pa.types.is_struct(arrow_type)
        or pa.types.is_list(arrow_type)
        or pa.types.is_map(arrow_type)
    ):
        return FieldType.json
    return FieldType.unknown


@register
class FilesConnector(Connector):
    scheme = "file"
    aliases = ("s3",)

    def _fs_and_path(self, uri: str):
        from pyarrow import fs as pafs

        return pafs.FileSystem.from_uri(uri)

    def list_assets(self, uri: str) -> list[str]:
        from pyarrow import fs as pafs

        filesystem, base = self._fs_and_path(uri)
        selector = pafs.FileSelector(base, recursive=True)
        infos = filesystem.get_file_info(selector)
        names = [
            info.path[len(base) :].lstrip("/")
            for info in infos
            if info.type == pafs.FileType.File and info.path.endswith(_EXTENSIONS)
        ]
        return sorted(names)

    def _read_table(self, uri: str, native_name: str):
        filesystem, base = self._fs_and_path(uri)
        path = f"{base.rstrip('/')}/{native_name}"
        if filesystem.get_file_info(path).type.name == "NotFound":
            raise KeyError(f"No file '{native_name}' under {uri}")
        if native_name.endswith(".parquet"):
            import pyarrow.parquet as pq

            with filesystem.open_input_file(path) as f:
                return pq.read_table(f)
        import pyarrow.csv as pacsv

        with filesystem.open_input_stream(path) as f:
            return pacsv.read_csv(f)

    def introspect(self, uri: str, native_name: str) -> AssetSchema:
        table = self._read_table(uri, native_name)
        return AssetSchema(
            fields=[
                FieldDef(
                    name=field.name,
                    type=canonical_type(field.type),
                    nullable=field.nullable,
                )
                for field in table.schema
            ]
        )

    def fetch(
        self,
        descriptor: AssetDescriptor,
        *,
        filters: Mapping[str, Any] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> FetchResult:
        import pyarrow.compute as pc

        filters = dict(filters or {})
        for field in filters:
            if descriptor.asset_schema.field(field) is None:
                raise KeyError(field)
        table = self._read_table(descriptor.source.uri, descriptor.source.native_name)
        for name, value in filters.items():
            table = table.filter(pc.equal(table[name], value))
        total = table.num_rows
        return FetchResult(records=table.slice(offset, limit).to_pylist(), total=total)
