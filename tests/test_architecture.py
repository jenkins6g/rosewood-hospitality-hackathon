from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ArchitectureTests(unittest.TestCase):
    def test_harness_prompt_is_thin(self) -> None:
        harness = (ROOT / "src" / "app" / "prompts" / "harness.md").read_text(encoding="utf-8")
        self.assertLessEqual(len(harness.split()), 120)

    def test_skill_files_exist(self) -> None:
        skills = sorted((ROOT / "src" / "app" / "skills").glob("*.md"))
        self.assertGreaterEqual(len(skills), 5)

    def test_skill_files_use_frontmatter(self) -> None:
        for path in sorted((ROOT / "src" / "app" / "skills").glob("*.md")):
            text = path.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("---\n"), f"{path.name} missing frontmatter")
            self.assertIn("\nname:", text, f"{path.name} missing skill name")
            self.assertIn("\ndescription:", text, f"{path.name} missing description")

    def test_agent_uses_resolver_and_skill_context(self) -> None:
        agent_text = (ROOT / "src" / "app" / "agent.py").read_text(encoding="utf-8")
        nodes_text = (ROOT / "src" / "app" / "graph" / "nodes.py").read_text(encoding="utf-8")
        self.assertIn("SkillResolver", agent_text)
        self.assertIn("ActionClassifier", agent_text)
        self.assertIn("build_context_bundle", nodes_text)

    def test_docs_lookup_indexes_skills_and_scaffold(self) -> None:
        config_text = (ROOT / "src" / "app" / "config.py").read_text(encoding="utf-8")
        registry_text = (ROOT / "src" / "app" / "tools" / "registry.py").read_text(encoding="utf-8")
        self.assertIn("REACT_CHATBOT_LANGCHAIN_PYTHON_SCAFFOLD.md", config_text)
        self.assertIn("skill_dir.glob(\"*.md\")", registry_text)

    def test_tool_registry_includes_web_and_flight_tools(self) -> None:
        registry_text = (ROOT / "src" / "app" / "tools" / "registry.py").read_text(encoding="utf-8")
        self.assertIn("build_web_search", registry_text)
        self.assertIn("build_flight_status", registry_text)


if __name__ == "__main__":
    unittest.main()
