"""
Neo4j Graph Builder.

Turns ParsedFile objects into a property graph:

  (:File)-[:CONTAINS]->(:Function)
  (:File)-[:CONTAINS]->(:Class)
  (:Class)-[:HAS_METHOD]->(:Function)
  (:Function)-[:CALLS]->(:Function)   (best-effort name matching)
  (:File)-[:IMPORTS]->(:File)
"""

import logging
from neo4j import GraphDatabase

from parser.ast_parser.parser import ParsedFile

logger = logging.getLogger(__name__)


class GraphBuilder:
    def __init__(self, uri: str = "bolt://localhost:7687", user: str = "neo4j", password: str = "codebaseai"):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build(self, parsed_files: list[ParsedFile]) -> None:
        with self.driver.session() as session:
            for pf in parsed_files:
                session.execute_write(self._create_file_node, pf)
                session.execute_write(self._create_function_nodes, pf)
                session.execute_write(self._create_class_nodes, pf)
                session.execute_write(self._create_import_edges, pf)
        logger.info(f"Graph built for {len(parsed_files)} files")

    # ------------------------------------------------------------------
    # Cypher writers
    # ------------------------------------------------------------------

    @staticmethod
    def _create_file_node(tx, pf: ParsedFile):
        tx.run(
            "MERGE (f:File {path: $path})",
            path=pf.file,
        )

    @staticmethod
    def _create_function_nodes(tx, pf: ParsedFile):
        for func in pf.functions:
            tx.run(
                """
                MERGE (fn:Function {name: $name, file: $file})
                SET fn.start_line = $start, fn.end_line = $end
                WITH fn
                MATCH (f:File {path: $file})
                MERGE (f)-[:CONTAINS]->(fn)
                """,
                name=func.name,
                file=pf.file,
                start=func.start_line,
                end=func.end_line,
            )
            # CALLS edges (best-effort — callee may not exist yet)
            for callee in func.calls:
                tx.run(
                    """
                    MERGE (caller:Function {name: $caller, file: $file})
                    MERGE (callee:Function {name: $callee})
                    MERGE (caller)-[:CALLS]->(callee)
                    """,
                    caller=func.name,
                    file=pf.file,
                    callee=callee,
                )

    @staticmethod
    def _create_class_nodes(tx, pf: ParsedFile):
        for cls in pf.classes:
            tx.run(
                """
                MERGE (c:Class {name: $name, file: $file})
                SET c.start_line = $start, c.end_line = $end
                WITH c
                MATCH (f:File {path: $file})
                MERGE (f)-[:CONTAINS]->(c)
                """,
                name=cls.name,
                file=pf.file,
                start=cls.start_line,
                end=cls.end_line,
            )
            for method in cls.methods:
                tx.run(
                    """
                    MERGE (m:Function {name: $name, file: $file, class: $cls})
                    SET m.start_line = $start, m.end_line = $end
                    WITH m
                    MATCH (c:Class {name: $cls, file: $file})
                    MERGE (c)-[:HAS_METHOD]->(m)
                    """,
                    name=method.name,
                    file=pf.file,
                    cls=cls.name,
                    start=method.start_line,
                    end=method.end_line,
                )

    @staticmethod
    def _create_import_edges(tx, pf: ParsedFile):
        for imp in pf.imports:
            tx.run(
                """
                MATCH (src:File {path: $src})
                MERGE (dep:Module {name: $dep})
                MERGE (src)-[:IMPORTS]->(dep)
                """,
                src=pf.file,
                dep=imp,
            )
