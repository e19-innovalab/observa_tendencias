"""Connector classes by name. config/sources.yaml selects one per source with `connector:`."""
from app.connectors.base import BaseConnector
from app.connectors.datos_argentina import DatosArgentinaConnector
from app.connectors.ilostat import IlostatConnector
from app.connectors.reference_table import ReferenceTableConnector
from app.connectors.simel import SimelConnector
from app.connectors.world_bank import WorldBankConnector
from app.core.config_files import SourceConf, catalog

CONNECTORS: dict[str, type[BaseConnector]] = {
    "world_bank": WorldBankConnector,
    "ilostat": IlostatConnector,
    "datos_argentina": DatosArgentinaConnector,
    "reference_table": ReferenceTableConnector,
    "simel": SimelConnector,
}


def build_connector(source: SourceConf) -> BaseConnector | None:
    cls = CONNECTORS.get(source.connector or "")
    if cls is None:
        return None
    return cls(source, [c.iso3 for c in catalog().countries])
