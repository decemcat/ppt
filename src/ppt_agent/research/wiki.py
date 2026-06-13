from __future__ import annotations
from rich.console import Console
from rich.table import Table
from rich.tree import Tree
from rich.prompt import Prompt
from rich.panel import Panel

from ppt_agent.research.knowledge_graph import KnowledgeGraph
from ppt_agent.research.chroma_indexer import ChromaIndexer

console = Console()


class WikiCLI:
    def __init__(self, graph: KnowledgeGraph, indexer: ChromaIndexer):
        self.graph = graph
        self.indexer = indexer

    def run(self):
        console.print(Panel("[bold]LLM Wiki Browser[/bold]\n"
                           "Commands: search <query> | graph <node> | stats | tree | help | quit", style="blue"))
        while True:
            cmd = Prompt.ask("[bold wiki]").strip()
            if cmd == "quit":
                break
            elif cmd == "help":
                console.print("  search <q> — semantic search\n  graph <id> — show related nodes\n  stats — graph stats\n  tree — show all nodes")
            elif cmd.startswith("search "):
                self._handle_search(cmd[7:])
            elif cmd.startswith("graph "):
                self._handle_graph(cmd[6:])
            elif cmd == "stats":
                self._handle_stats()
            elif cmd == "tree":
                self._handle_tree()
            else:
                console.print("[yellow]Unknown command. Type help.[/yellow]")

    def _handle_search(self, query: str):
        results = self.indexer.search(query, top_k=5)
        if not results:
            console.print("[yellow]No results.[/yellow]")
            return
        table = Table(title=f"Search: {query}")
        table.add_column("ID", style="dim")
        table.add_column("Snippet")
        table.add_column("Source")
        for r in results:
            table.add_row(r["id"][:20], r["text"][:80], r["metadata"].get("source", "?"))
        console.print(table)

    def _handle_graph(self, node_id: str):
        node = self.graph.get_node(node_id)
        if not node:
            console.print(f"[yellow]Node '{node_id}' not found.[/yellow]")
            return
        related = self.graph.get_related(node_id)
        tree = Tree(f"[bold]{node.label}[/bold] ({node.type})")
        for r in related:
            tree.add(f"{r.label} ({r.type})")
        console.print(tree)

    def _handle_stats(self):
        stats = self.graph.count()
        chroma_count = self.indexer.count()
        console.print(f"[green]Knowledge Graph:[/green] {stats['nodes']} nodes, {stats['edges']} edges")
        console.print(f"[green]Vector Store:[/green] {chroma_count} documents")

    def _handle_tree(self):
        tree = Tree("[bold]Knowledge Graph[/bold]")
        nodes = {}
        for node_id in self.graph._graph.nodes:
            data = self.graph._graph.nodes[node_id]
            ntype = data.get("type", "concept")
            if ntype not in nodes:
                nodes[ntype] = Tree(f"[blue]{ntype}[/blue]")
            nodes[ntype].add(f"{data.get('label', node_id)} [dim]{node_id}[/dim]")
        for ntype, subtree in nodes.items():
            tree.add(subtree)
        console.print(tree)


class WikiServer:
    def __init__(self, graph: KnowledgeGraph, indexer: ChromaIndexer, host: str = "127.0.0.1", port: int = 8765):
        self.graph = graph
        self.indexer = indexer
        self.host = host
        self.port = port

    def run(self):
        try:
            from flask import Flask, jsonify, request, render_template_string
        except ImportError:
            console.print("[red]Flask not installed. Run: pip install flask[/red]")
            return

        app = Flask(__name__)

        @app.route("/")
        def index():
            stats = self.graph.count()
            html = f"""<html><head><title>LLM Wiki</title>
            <style>body{{font-family:sans-serif;max-width:900px;margin:auto;padding:20px}}
            .node{{border:1px solid #ddd;padding:10px;margin:5px;border-radius:5px}}
            .node:hover{{background:#f5f5f5}}</style></head>
            <body><h1>LLM Wiki</h1>
            <form action="/search" method="get">
            <input name="q" size="40" placeholder="Search knowledge base...">
            <button>Search</button>
            </form>
            <p>{stats['nodes']} nodes, {stats['edges']} edges</p>
            <h2>Graph Visualization</h2>
            <div id="graph" style="width:100%;height:500px;border:1px solid #ccc"></div>
            <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
            <script>
            fetch('/api/graph').then(r=>r.json()).then(data=>{{
                var nodes=new vis.DataSet(data.nodes);
                var edges=new vis.DataSet(data.edges);
                var container=document.getElementById('graph');
                new vis.Network(container,{{nodes:nodes,edges:edges}},{{physics:false}});
            }});
            </script></body></html>"""
            return render_template_string(html)

        @app.route("/search")
        def search():
            q = request.args.get("q", "")
            results = self.indexer.search(q, top_k=10)
            items = "".join(f'<div class="node"><b>{r["id"]}</b><p>{r["text"][:200]}</p><small>source: {r["metadata"].get("source","?")}</small></div>'
                          for r in results)
            return f"<html><body><h1>Search: {q}</h1>{items}<a href='/'>Back</a></body></html>"

        @app.route("/api/graph")
        def api_graph():
            nodes = []
            edges = []
            for nid in self.graph._graph.nodes:
                data = self.graph._graph.nodes[nid]
                nodes.append({"id": nid, "label": data.get("label", nid), "group": data.get("type", "concept")})
            for u, v, d in self.graph._graph.edges(data=True):
                edges.append({"from": u, "to": v, "label": d.get("relation", "")})
            return jsonify({"nodes": nodes, "edges": edges})

        console.print(f"[green]Wiki server started at http://{self.host}:{self.port}[/green]")
        app.run(host=self.host, port=self.port, debug=False)
