from __future__ import annotations
from datetime import datetime
from ppt_agent.research.models import RepoAnalysis
from ppt_agent.research.content_extractor import extract_readme_summary


class GitHubAnalyzer:
    def __init__(self, token: str = ""):
        self.token = token

    def search(self, query: str, max_results: int = 5) -> list[RepoAnalysis]:
        try:
            return self._search_pygithub(query, max_results)
        except ImportError:
            return self._search_gh_cli(query, max_results)

    def _search_pygithub(self, query: str, max_results: int) -> list[RepoAnalysis]:
        from github import Github
        g = Github(self.token) if self.token else Github()
        repos = g.search_repositories(query, sort="stars", order="desc")
        results = []
        for repo in repos[:max_results]:
            readme_text = ""
            try:
                readme_text = repo.get_readme().decoded_content.decode("utf-8")
            except Exception:
                pass
            results.append(RepoAnalysis(
                repo=repo.full_name, description=repo.description or "",
                stars=repo.stargazers_count, topics=repo.get_topics(),
                readme_summary=extract_readme_summary(readme_text),
                last_commit=repo.updated_at if repo.updated_at else datetime.now(),
            ))
        return results

    def _search_gh_cli(self, query: str, max_results: int) -> list[RepoAnalysis]:
        import subprocess, json
        result = subprocess.run(
            ["gh", "search", "repos", query, "--json",
             "name,owner,description,stargazersCount", f"--limit={max_results}"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return []
        try:
            data = json.loads(result.stdout)
            return [RepoAnalysis(
                repo=f"{item['owner']['login']}/{item['name']}",
                description=item.get("description", ""),
                stars=item.get("stargazersCount", 0),
            ) for item in data]
        except (json.JSONDecodeError, KeyError):
            return []

    def analyze_repo(self, repo_full_name: str) -> RepoAnalysis | None:
        results = self._search_pygithub(repo_full_name, 1)
        return results[0] if results else None
