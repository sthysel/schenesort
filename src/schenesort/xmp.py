"""XMP sidecar file handling for image metadata."""

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

import defusedxml.ElementTree as DefusedET

# XML namespaces
NAMESPACES = {
    "x": "adobe:ns:meta/",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "dc": "http://purl.org/dc/elements/1.1/",
    "schenesort": "http://github.com/sthysel/schenesort/",
}

# Register namespaces for writing
for prefix, uri in NAMESPACES.items():
    ET.register_namespace(prefix, uri)


@dataclass
class ImageMetadata:
    """Metadata for a wallpaper image."""

    description: str = ""
    tags: list[str] = field(default_factory=list)
    mood: list[str] = field(default_factory=list)
    style: str = ""
    colors: list[str] = field(default_factory=list)
    time_of_day: str = ""
    subject: str = ""
    source: str = ""
    ai_model: str = ""

    def is_empty(self) -> bool:
        return not any(
            [
                self.description,
                self.tags,
                self.mood,
                self.style,
                self.colors,
                self.time_of_day,
                self.subject,
                self.source,
                self.ai_model,
            ]
        )


def get_xmp_path(image_path: Path) -> Path:
    """Get the XMP sidecar path for an image."""
    return image_path.parent / f"{image_path.name}.xmp"


def read_xmp(image_path: Path) -> ImageMetadata:
    """Read metadata from XMP sidecar file."""
    xmp_path = get_xmp_path(image_path)

    if not xmp_path.exists():
        return ImageMetadata()

    try:
        tree = DefusedET.parse(xmp_path)
        root = tree.getroot()

        metadata = ImageMetadata()

        # Find the Description element
        desc_elem = root.find(".//rdf:Description", NAMESPACES)
        if desc_elem is None:
            return metadata

        # Read description
        dc_desc = desc_elem.find("dc:description", NAMESPACES)
        if dc_desc is not None:
            # Handle both simple text and Alt/li structure
            alt = dc_desc.find("rdf:Alt/rdf:li", NAMESPACES)
            if alt is not None and alt.text:
                metadata.description = alt.text
            elif dc_desc.text:
                metadata.description = dc_desc.text

        # Read tags
        dc_subject = desc_elem.find("dc:subject/rdf:Bag", NAMESPACES)
        if dc_subject is not None:
            for li in dc_subject.findall("rdf:li", NAMESPACES):
                if li.text:
                    metadata.tags.append(li.text)

        # Read source
        dc_source = desc_elem.find("dc:source", NAMESPACES)
        if dc_source is not None and dc_source.text:
            metadata.source = dc_source.text

        # Read AI model
        ai_model = desc_elem.find("schenesort:ai_model", NAMESPACES)
        if ai_model is not None and ai_model.text:
            metadata.ai_model = ai_model.text

        # Read mood
        mood_elem = desc_elem.find("schenesort:mood/rdf:Bag", NAMESPACES)
        if mood_elem is not None:
            for li in mood_elem.findall("rdf:li", NAMESPACES):
                if li.text:
                    metadata.mood.append(li.text)

        # Read style
        style_elem = desc_elem.find("schenesort:style", NAMESPACES)
        if style_elem is not None and style_elem.text:
            metadata.style = style_elem.text

        # Read colors
        colors_elem = desc_elem.find("schenesort:colors/rdf:Bag", NAMESPACES)
        if colors_elem is not None:
            for li in colors_elem.findall("rdf:li", NAMESPACES):
                if li.text:
                    metadata.colors.append(li.text)

        # Read time of day
        time_elem = desc_elem.find("schenesort:time_of_day", NAMESPACES)
        if time_elem is not None and time_elem.text:
            metadata.time_of_day = time_elem.text

        # Read subject
        subject_elem = desc_elem.find("schenesort:subject", NAMESPACES)
        if subject_elem is not None and subject_elem.text:
            metadata.subject = subject_elem.text

        return metadata

    except Exception:
        return ImageMetadata()


def write_xmp(image_path: Path, metadata: ImageMetadata) -> None:
    """Write metadata to XMP sidecar file."""
    xmp_path = get_xmp_path(image_path)

    # Build XMP structure
    root = ET.Element(f"{{{NAMESPACES['x']}}}xmpmeta")

    rdf = ET.SubElement(root, f"{{{NAMESPACES['rdf']}}}RDF")
    desc = ET.SubElement(rdf, f"{{{NAMESPACES['rdf']}}}Description")

    # Add description
    if metadata.description:
        dc_desc = ET.SubElement(desc, f"{{{NAMESPACES['dc']}}}description")
        alt = ET.SubElement(dc_desc, f"{{{NAMESPACES['rdf']}}}Alt")
        li = ET.SubElement(alt, f"{{{NAMESPACES['rdf']}}}li")
        li.set(f"{{{NAMESPACES['rdf']}}}parseType", "Literal")
        li.text = metadata.description

    # Add tags
    if metadata.tags:
        dc_subject = ET.SubElement(desc, f"{{{NAMESPACES['dc']}}}subject")
        bag = ET.SubElement(dc_subject, f"{{{NAMESPACES['rdf']}}}Bag")
        for tag in metadata.tags:
            li = ET.SubElement(bag, f"{{{NAMESPACES['rdf']}}}li")
            li.text = tag

    # Add source
    if metadata.source:
        dc_source = ET.SubElement(desc, f"{{{NAMESPACES['dc']}}}source")
        dc_source.text = metadata.source

    # Add AI model
    if metadata.ai_model:
        ai_model = ET.SubElement(desc, f"{{{NAMESPACES['schenesort']}}}ai_model")
        ai_model.text = metadata.ai_model

    # Add mood
    if metadata.mood:
        mood_elem = ET.SubElement(desc, f"{{{NAMESPACES['schenesort']}}}mood")
        bag = ET.SubElement(mood_elem, f"{{{NAMESPACES['rdf']}}}Bag")
        for mood in metadata.mood:
            li = ET.SubElement(bag, f"{{{NAMESPACES['rdf']}}}li")
            li.text = mood

    # Add style
    if metadata.style:
        style_elem = ET.SubElement(desc, f"{{{NAMESPACES['schenesort']}}}style")
        style_elem.text = metadata.style

    # Add colors
    if metadata.colors:
        colors_elem = ET.SubElement(desc, f"{{{NAMESPACES['schenesort']}}}colors")
        bag = ET.SubElement(colors_elem, f"{{{NAMESPACES['rdf']}}}Bag")
        for color in metadata.colors:
            li = ET.SubElement(bag, f"{{{NAMESPACES['rdf']}}}li")
            li.text = color

    # Add time of day
    if metadata.time_of_day:
        time_elem = ET.SubElement(desc, f"{{{NAMESPACES['schenesort']}}}time_of_day")
        time_elem.text = metadata.time_of_day

    # Add subject
    if metadata.subject:
        subject_elem = ET.SubElement(desc, f"{{{NAMESPACES['schenesort']}}}subject")
        subject_elem.text = metadata.subject

    # Write to file
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")

    with open(xmp_path, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        tree.write(f, encoding="unicode")
        f.write("\n")
