"""Python wrapper for OpenOLAT JQTI+ validation engine.

Validates QTI 2.1 items, tests, and packages against OpenOLAT's native
Java QTI 2.1 runtime (JQTI+ / qtiworks).
"""

import json
import os
import shutil
import subprocess
import tempfile
import urllib.request
from pathlib import Path
from typing import List, Optional, Tuple, Union

CACHE_DIR = Path(__file__).resolve().parent.parent / ".jqti_cache"
JAVA_SRC_DIR = Path(__file__).resolve().parent / "java"

JARS = {
    "qtiworks-jqtiplus-1.0.37.jar": (
        "https://nexus.openolat.org/nexus/content/groups/public/org/openolat/qtiworks/qtiworks-jqtiplus/1.0.37/qtiworks-jqtiplus-1.0.37.jar"
    ),
    "slf4j-api-1.7.36.jar": (
        "https://repo1.maven.org/maven2/org/slf4j/slf4j-api/1.7.36/slf4j-api-1.7.36.jar"
    ),
    "slf4j-simple-1.7.36.jar": (
        "https://repo1.maven.org/maven2/org/slf4j/slf4j-simple/1.7.36/slf4j-simple-1.7.36.jar"
    ),
    "htmlparser-1.4.16.jar": (
        "https://repo1.maven.org/maven2/nu/validator/htmlparser/1.4.16/htmlparser-1.4.16.jar"
    ),
}


def is_java_available() -> bool:
    """Return True if Java is installed and accessible on PATH."""
    try:
        res = subprocess.run(["java", "-version"], capture_output=True, text=True)
        return res.returncode == 0
    except (FileNotFoundError, OSError):
        return False


def is_javac_available() -> bool:
    """Return True if javac is installed and accessible on PATH."""
    try:
        res = subprocess.run(["javac", "-version"], capture_output=True, text=True)
        return res.returncode == 0
    except (FileNotFoundError, OSError):
        return False


def ensure_jqti_environment(cache_dir: Optional[Path] = None) -> Path:
    """Ensure JQTI+ JARs are downloaded and QtiValidator is compiled.

    Returns the cache directory containing the classes and JARs.
    Raises RuntimeError if Java or javac is not available.
    """
    if not is_java_available() or not is_javac_available():
        raise RuntimeError("Java and javac must be installed to use the JQTI+ validator.")

    target_dir = cache_dir or CACHE_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    classes_dir = target_dir / "classes"
    classes_dir.mkdir(parents=True, exist_ok=True)

    # 1. Download missing JARs
    for jar_name, url in JARS.items():
        jar_path = target_dir / jar_name
        if not jar_path.exists() or jar_path.stat().st_size == 0:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (QTI-Creator-Validator)"})
            with urllib.request.urlopen(req) as resp:
                jar_path.write_bytes(resp.read())

    # 2. Build classpath
    jar_paths = list(target_dir.glob("*.jar"))
    classpath = ":".join(str(p) for p in jar_paths)

    # 3. Check if compilation is needed
    validator_src = JAVA_SRC_DIR / "org" / "qticreator" / "validator" / "QtiValidator.java"
    validator_class = classes_dir / "org" / "qticreator" / "validator" / "QtiValidator.class"

    compile_needed = (
        not validator_class.exists()
        or validator_class.stat().st_mtime < validator_src.stat().st_mtime
    )

    if compile_needed:
        cmd = [
            "javac",
            "-cp",
            classpath,
            "-d",
            str(classes_dir),
            str(validator_src),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"Failed to compile QtiValidator.java: {res.stderr}")

    return target_dir


def validate_with_jqti(paths: List[Union[str, Path]]) -> Tuple[bool, List[str]]:
    """Validate a list of XML files or ZIP packages against the JQTI+ runtime.

    Returns:
        (is_valid, list_of_error_messages)
    """
    target_dir = ensure_jqti_environment()
    classes_dir = target_dir / "classes"
    jar_paths = list(target_dir.glob("*.jar"))
    classpath = f"{classes_dir}:" + ":".join(str(p) for p in jar_paths)

    cmd = [
        "java",
        "-cp",
        classpath,
        "org.qticreator.validator.QtiValidator",
        "--json",
    ] + [str(p) for p in paths]

    res = subprocess.run(cmd, capture_output=True, text=True)
    try:
        data = json.loads(res.stdout)
        is_valid = bool(data.get("valid", False))
        error_msgs = [f"[{e['file']}] {e['message']}" for e in data.get("errors", [])]
        return is_valid, error_msgs
    except Exception as e:
        if res.returncode != 0 and res.stderr:
            return False, [res.stderr.strip()]
        raise RuntimeError(f"Unexpected output from JQTI+ validator: {res.stdout}") from e


def validate_qti_xml_string(xml_content: str, filename: str = "item.xml") -> Tuple[bool, List[str]]:
    """Validate an XML string directly against JQTI+."""
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / filename
        p.write_text(xml_content, encoding="utf-8")
        return validate_with_jqti([p])


def validate_qti_zip_bytes(zip_bytes: bytes) -> Tuple[bool, List[str]]:
    """Validate an in-memory ZIP package directly against JQTI+."""
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tf:
        tf.write(zip_bytes)
        tf_path = tf.name

    try:
        return validate_with_jqti([tf_path])
    finally:
        if os.path.exists(tf_path):
            os.remove(tf_path)
