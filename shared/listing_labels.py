"""Airbnb listing name to short-label mapping used by both pipelines."""

LISTING_LABELS: dict[str, str] = {
    "Totalmente Renovado, metro à porta": "T2",
    "Estúdio Renovado c/ metro à porta": "T0",
    "T1 Renovado c/ metro à porta": "T1",
    "Espaço Renovado a 5 minutos a pé da Ponte Luíz I": "EA",
    "Loft c/ Varanda Solarenga a 5 Minutos Ponte Luíz I": "EB",
}

LABEL_ORDER = ["T0", "T1", "T2", "EA", "EB"]
