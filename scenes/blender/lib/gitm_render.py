"""Shared Blender render settings."""


def strip_metadata(scene):
    """Turn off every PNG metadata stamp (date, render time, ...) so identical pixels give identical bytes."""
    for prop in scene.render.bl_rna.properties:
        if prop.identifier.startswith("use_stamp") and not prop.is_readonly:
            setattr(scene.render, prop.identifier, False)
