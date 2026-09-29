"""Versioned PoC schema and deliberately small approved terminology library."""
from decimal import Decimal, InvalidOperation
import json
import re

SCHEMA_VERSION = "motor-v2"
POLICY_VERSION = "evidence-policy-v2"
TERMINOLOGY_VERSION = "motor-terms-v1"
FIELDS = ("manufacturer", "part_number", "family", "voltage", "frequency", "power", "certification")
REQUIRED = ("manufacturer", "part_number", "family", "voltage", "frequency", "power")
PROTECTED = ("voltage", "frequency", "power")
ALIASES = {
    "manufacturer": ["manufacturer", "hersteller", "fabricante", "الشركة المصنعة"],
    "part_number": ["part number", "teilenummer", "referencia", "رقم الجزء"],
    "family": ["family", "familie", "familia", "العائلة"],
    "voltage": ["voltage", "spannung", "tensión", "الجهد"],
    "frequency": ["frequency", "frequenz", "frecuencia", "التردد"],
    "power": ["power", "leistung", "potencia", "القدرة"],
    "certification": ["certification", "zertifizierung", "certificación", "الشهادة"],
}
MARKETS = {
    "en-US": {"language": "en", "locale": "en-US", "required": list(REQUIRED), "title": "Electric motor", "decimal": "."},
    "de-DE": {"language": "de", "locale": "de-DE", "required": list(REQUIRED), "title": "Elektromotor", "decimal": ","},
    "es-ES": {"language": "es", "locale": "es-ES", "required": list(REQUIRED), "title": "Motor eléctrico", "decimal": ","},
    "es-MX": {"language": "es", "locale": "es-MX", "required": [*REQUIRED, "certification"], "title": "Motor eléctrico", "decimal": "."},
    "ar-SA": {"language": "ar", "locale": "ar-SA", "required": list(REQUIRED), "title": "محرك كهربائي", "decimal": "."},
}
# es-MX certification requirement is a fictional organizational rule, not law.
LABELS = {lang: {field: names[idx] for field, names in ALIASES.items()}
          for idx, lang in enumerate(("en", "de", "es", "ar"))}
ALIASES["manufacturer"] += ["المصنع"]
ALIASES["part_number"] += ["mpn", "artikelnummer", "número de pieza", "رقم القطعة"]
ALIASES["family"] += ["series", "baureihe", "serie", "السلسلة"]
ALIASES["voltage"] += ["rated voltage", "nennspannung", "tensión nominal", "الجهد المقنن"]
ALIASES["frequency"] += ["rated frequency", "nennfrequenz", "frecuencia nominal", "التردد المقنن"]
ALIASES["power"] += ["rated power", "nennleistung", "potencia nominal", "القدرة المقننة"]


def labeled_parts(segment):
    """Approved text/table/flat-JSON grammars; preserve the original quote elsewhere."""
    text = segment.strip()
    if text.startswith('"'):
        try:
            pair = json.loads("{" + text.rstrip(",") + "}")
            if len(pair) == 1:
                label, value = next(iter(pair.items()))
                if isinstance(value, str):
                    return label, value
        except (ValueError, TypeError):
            return None
    if text.startswith("|") and text.endswith("|"):
        cells = [v.strip() for v in text[1:-1].split("|")]
        return tuple(cells) if len(cells) == 2 else None
    parts = re.split(r"[:=]", text, maxsplit=1)
    return tuple(p.strip() for p in parts) if len(parts) == 2 else None


def segment_field(segment):
    parts = labeled_parts(segment)
    return next((key for key, names in ALIASES.items() if parts[0].casefold() in names), None) if parts else None


def canonical_number(value):
    number = Decimal(str(value))
    if not number.is_finite():
        raise ValueError("non-finite number")
    return format(number.normalize(), "f")


def parse_segment(segment):
    """Accept only one complete labeled fact; general prose requires review.

    The narrow grammar is intentional: quoting a document is not enough to prove
    entailment. Values are reconstructed from the source, never trusted from LLMs.
    """
    parts = labeled_parts(segment)
    if parts is None:
        return None
    label, raw = parts
    field = segment_field(segment)
    if field is None:
        return None
    if field in PROTECTED:
        normalized_raw = raw.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩٫", "0123456789."))
        match = re.fullmatch(r"([0-9]+(?:[.,][0-9]+)?)\s*(V|kV|Hz|kHz|W|kW)", normalized_raw)
        if not match:
            return None
        value, unit = match.groups()
        allowed = {"voltage": {"V": ("V", 1), "kV": ("V", 1000)},
                   "frequency": {"Hz": ("Hz", 1), "kHz": ("Hz", 1000)},
                   "power": {"W": ("W", 1), "kW": ("W", 1000)}}
        if unit not in allowed[field]:
            return None
        canonical_unit, factor = allowed[field][unit]
        number = Decimal(value.replace(",", "."))
        if number <= 0:
            return None
        return {"field": field, "value": canonical_number(number * factor), "unit": canonical_unit,
                "status": "derived" if factor != 1 or "," in value or normalized_raw != raw else "explicit",
                "rule": f"decimal-exact:{unit}->{canonical_unit}:multiply-{factor}", "original_value": raw}
    patterns = {"manufacturer": r"[A-Za-z][A-Za-z0-9 .&-]{0,59}",
                "part_number": r"[A-Z0-9][A-Z0-9-]{1,39}",
                "family": r"[A-Z0-9][A-Z0-9-]{1,39}",
                "certification": r"TEST-CERT-[A-Z0-9-]+"}
    if not re.fullmatch(patterns[field], raw):
        return None
    return {"field": field, "value": raw, "unit": None, "status": "explicit",
            "rule": "literal-identifier-v1", "original_value": raw}


def segments(text):
    """Offsets refer to Python Unicode code points in the original source text."""
    return [(m.group().strip(), m.start() + len(m.group()) - len(m.group().lstrip()))
            for m in re.finditer(r"[^;\n]+", text) if m.group().strip()]


def same_value(field, proposed, actual):
    try:
        if field in PROTECTED:
            return canonical_number(proposed) == actual
        return isinstance(proposed, str) and proposed == actual
    except (ValueError, InvalidOperation, TypeError):
        return False
