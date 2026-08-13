from docwarden.config import DensityConfig, FileLengthConfig
from docwarden.density.rules import check_file_length, check_front_matter_description
from docwarden.markdown import parse


def test_file_length_no_finding_under_threshold():
    doc = parse("line\n" * 10)
    config = DensityConfig(file_length=FileLengthConfig(default_threshold=400))

    assert check_file_length("a.md", doc, config) == []


def test_file_length_finding_over_default_threshold():
    doc = parse("line\n" * 500)
    config = DensityConfig(file_length=FileLengthConfig(default_threshold=400))

    findings = check_file_length("a.md", doc, config)

    assert len(findings) == 1
    f = findings[0]
    assert f.rule == "density/file-length"
    assert f.path == "a.md"
    assert f.fingerprint == "file"
    assert "500" in f.message and "400" in f.message


def test_file_length_uses_basename_specific_threshold():
    doc = parse("line\n" * 460)
    config = DensityConfig(
        file_length=FileLengthConfig(default_threshold=400, thresholds={"SKILL.md": 500})
    )

    assert check_file_length(".claude/skills/x/SKILL.md", doc, config) == []
    assert len(check_file_length("other.md", doc, config)) == 1


def test_front_matter_description_disabled_by_default():
    doc = parse("---\nname: x\ndescription: " + ("a" * 600) + "\n---\n")
    config = DensityConfig()  # front_matter_description_enabled defaults to False

    assert check_front_matter_description("SKILL.md", doc, config) == []


def test_front_matter_description_no_finding_under_threshold():
    doc = parse("---\nname: x\ndescription: short\n---\n")
    config = DensityConfig(front_matter_description_enabled=True, front_matter_description_threshold=500)

    assert check_front_matter_description("SKILL.md", doc, config) == []


def test_front_matter_description_finding_over_threshold():
    long_desc = "a" * 600
    doc = parse(f"---\nname: x\ndescription: {long_desc}\n---\n")
    config = DensityConfig(front_matter_description_enabled=True, front_matter_description_threshold=500)

    findings = check_front_matter_description("SKILL.md", doc, config)

    assert len(findings) == 1
    assert findings[0].rule == "density/front-matter-description"
    assert "600" in findings[0].message


def test_front_matter_description_ignored_for_non_skill_md():
    long_desc = "a" * 600
    doc = parse(f"---\nname: x\ndescription: {long_desc}\n---\n")
    config = DensityConfig(front_matter_description_enabled=True)

    assert check_front_matter_description("CLAUDE.md", doc, config) == []


def test_front_matter_description_no_finding_without_front_matter():
    doc = parse("# Just a heading\n")
    config = DensityConfig(front_matter_description_enabled=True)

    assert check_front_matter_description("SKILL.md", doc, config) == []
