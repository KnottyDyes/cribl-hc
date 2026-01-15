"""
Analyzes library entries, functions, and reusable resources to identify unused dependencies,
optimization opportunities, and maintenance overhead.
"""

import re
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field

from cribl_hc.analyzers.base import AnalyzerResult, BaseAnalyzer
from cribl_hc.core.api_client import CriblAPIClient


class LibraryEntry(BaseModel):
    """Represents a library entry with metadata."""

    id: str
    name: str
    type: str  # "function", "lookup", "pipeline", etc.
    size_bytes: int = 0
    function_count: int = 0
    last_modified: Optional[str] = None
    references: List[str] = Field(default_factory=list)  # IDs of things that reference this library
    content_hash: Optional[str] = None

    @property
    def is_large(self) -> bool:
        """Check if library is considered large (>1MB)."""
        return self.size_bytes > 1_000_000

    @property
    def has_many_functions(self) -> bool:
        """Check if library has many functions (>20)."""
        return self.function_count > 20


class UsageReference(BaseModel):
    """Represents a usage reference found in code."""

    library_id: str
    referenced_in: str  # pipeline, route, or function ID
    reference_type: str  # "function_call", "lookup_reference", etc.
    line_number: Optional[int] = None
    context: Optional[str] = None


class LibraryAndResourceAnalyzer(BaseAnalyzer):
    """
    Analyzes library entries, functions, and reusable resources to identify unused dependencies,
    optimization opportunities, and maintenance overhead.
    """

    @property
    def objective_name(self) -> str:
        return "library-resource-optimization"

    def get_description(self) -> str:
        return "Analyzes library usage patterns, identifies unused dependencies, and suggests optimization opportunities."

    def get_required_permissions(self) -> List[str]:
        return ["read:libraries", "read:functions", "read:pipelines", "read:routes", "read:lookups"]

    @property
    def supported_products(self) -> list[str]:
        return ["stream", "edge"]  # Libraries are primarily a Stream/Edge feature

    async def analyze(self, client: CriblAPIClient) -> AnalyzerResult:
        """
        Perform analysis on library and resource usage.
        """
        result = self.create_result()

        try:
            # Collect all library entries
            libraries = await self._get_libraries(client)

            if not libraries:
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id="no-libraries-found",
                        category="Configuration",
                        severity="info",
                        title="No Libraries Found",
                        description="No library entries were found for analysis.",
                        confidence_level="high",
                        affected_components=["libraries"],
                        remediation_steps=[
                            "Libraries are used to share reusable functions and lookups across pipelines."
                        ],
                    )
                )
                return result

            # Analyze usage patterns
            usage_references = await self._analyze_usage_patterns(client, libraries)

            # Perform various analyses
            self._check_unused_libraries(result, libraries, usage_references, client)
            self._check_performance_impact(result, libraries, usage_references, client)
            self._check_maintenance_burden(result, libraries, client)
            self._analyze_dependency_chains(result, libraries, usage_references, client)
            self._suggest_optimization_opportunities(result, libraries, usage_references, client)

        except Exception as e:
            self.log.error(f"Error during library and resource analysis: {e}", exc_info=True)
            result.success = False
            result.error = str(e)

        return result

    async def _get_libraries(self, client: CriblAPIClient) -> List[LibraryEntry]:
        """Fetch all library entries with metadata."""
        libraries = []

        try:
            # Get functions library
            functions_data = await client.get("lib/functions")
            for func_data in functions_data.get("items", []):
                lib = LibraryEntry(
                    id=f"function:{func_data.get('id', '')}",
                    name=func_data.get("name", ""),
                    type="function",
                    size_bytes=self._estimate_size(func_data),
                    function_count=1,  # Each function entry is one function
                    last_modified=func_data.get("lastModified"),
                    content_hash=self._calculate_content_hash(func_data),
                )
                libraries.append(lib)

        except Exception as e:
            self.log.debug(f"Could not fetch functions library: {e}")

        try:
            # Get lookups library
            lookups_data = await client.get("lib/lookups")
            for lookup_data in lookups_data.get("items", []):
                lib = LibraryEntry(
                    id=f"lookup:{lookup_data.get('id', '')}",
                    name=lookup_data.get("filename", ""),
                    type="lookup",
                    size_bytes=lookup_data.get("size", 0),
                    function_count=0,  # Lookups don't have functions
                    last_modified=lookup_data.get("lastModified"),
                    content_hash=self._calculate_content_hash(lookup_data),
                )
                libraries.append(lib)

        except Exception as e:
            self.log.debug(f"Could not fetch lookups library: {e}")

        try:
            # Get pipeline fragments (reusable pipeline components)
            fragments_data = await client.get("lib/pipelines")
            for frag_data in fragments_data.get("items", []):
                lib = LibraryEntry(
                    id=f"pipeline:{frag_data.get('id', '')}",
                    name=frag_data.get("name", ""),
                    type="pipeline_fragment",
                    size_bytes=self._estimate_size(frag_data),
                    function_count=self._count_functions_in_pipeline(frag_data),
                    last_modified=frag_data.get("lastModified"),
                    content_hash=self._calculate_content_hash(frag_data),
                )
                libraries.append(lib)

        except Exception as e:
            self.log.debug(f"Could not fetch pipeline fragments: {e}")

        return libraries

    async def _analyze_usage_patterns(
        self, client: CriblAPIClient, libraries: List[LibraryEntry]
    ) -> Dict[str, List[UsageReference]]:
        """Analyze how libraries are used across pipelines and routes."""
        usage_map = defaultdict(list)

        try:
            # Get all pipelines to analyze their library usage
            pipelines = await client.get_pipelines()
            routes = await client.get_routes()

            # Create lookup maps for faster searching
            function_libs = {lib.id: lib for lib in libraries if lib.type == "function"}
            lookup_libs = {lib.id: lib for lib in libraries if lib.type == "lookup"}
            pipeline_libs = {lib.id: lib for lib in libraries if lib.type == "pipeline_fragment"}

            # Analyze pipeline usage
            for pipeline in pipelines:
                pipeline_id = pipeline.get("id", "")
                pipeline_config = pipeline.get("config", {})

                # Check function usage
                await self._analyze_function_usage(
                    pipeline_config, pipeline_id, function_libs, usage_map
                )

                # Check lookup usage
                await self._analyze_lookup_usage(
                    pipeline_config, pipeline_id, lookup_libs, usage_map
                )

                # Check pipeline fragment usage
                await self._analyze_pipeline_fragment_usage(
                    pipeline_config, pipeline_id, pipeline_libs, usage_map
                )

            # Analyze route usage (routes can reference pipelines)
            for route in routes:
                route_id = route.get("id", "")
                pipeline_refs = route.get("pipelineRefs", [])

                for pipeline_ref in pipeline_refs:
                    if pipeline_ref in [lib.name for lib in pipeline_libs.values()]:
                        # Find the library that matches this reference
                        for lib_id, lib in pipeline_libs.items():
                            if lib.name == pipeline_ref:
                                usage_map[lib_id].append(
                                    UsageReference(
                                        library_id=lib_id,
                                        referenced_in=f"route:{route_id}",
                                        reference_type="pipeline_reference",
                                    )
                                )
                                lib.references.append(f"route:{route_id}")

        except Exception as e:
            self.log.warning(f"Error analyzing usage patterns: {e}")

        return usage_map

    async def _analyze_function_usage(
        self,
        pipeline_config: Dict[str, Any],
        pipeline_id: str,
        function_libs: Dict[str, LibraryEntry],
        usage_map: Dict[str, List[UsageReference]],
    ) -> None:
        """Analyze function usage within a pipeline."""
        try:
            # Extract function calls from pipeline configuration
            functions_used = self._extract_function_calls(pipeline_config)

            for func_name in functions_used:
                # Check if this function name matches any library function
                for lib_id, lib in function_libs.items():
                    if lib.name == func_name or func_name in lib.name:
                        usage_map[lib_id].append(
                            UsageReference(
                                library_id=lib_id,
                                referenced_in=f"pipeline:{pipeline_id}",
                                reference_type="function_call",
                            )
                        )
                        lib.references.append(f"pipeline:{pipeline_id}")
                        break
        except Exception as e:
            self.log.debug(f"Error analyzing function usage in pipeline {pipeline_id}: {e}")

    async def _analyze_lookup_usage(
        self,
        pipeline_config: Dict[str, Any],
        pipeline_id: str,
        lookup_libs: Dict[str, LibraryEntry],
        usage_map: Dict[str, List[UsageReference]],
    ) -> None:
        """Analyze lookup usage within a pipeline."""
        try:
            # Look for lookup references in pipeline configuration
            lookup_refs = self._extract_lookup_references(pipeline_config)

            for lookup_name in lookup_refs:
                for lib_id, lib in lookup_libs.items():
                    if lib.name == lookup_name or lookup_name in lib.name:
                        usage_map[lib_id].append(
                            UsageReference(
                                library_id=lib_id,
                                referenced_in=f"pipeline:{pipeline_id}",
                                reference_type="lookup_reference",
                            )
                        )
                        lib.references.append(f"pipeline:{pipeline_id}")
                        break
        except Exception as e:
            self.log.debug(f"Error analyzing lookup usage in pipeline {pipeline_id}: {e}")

    async def _analyze_pipeline_fragment_usage(
        self,
        pipeline_config: Dict[str, Any],
        pipeline_id: str,
        pipeline_libs: Dict[str, LibraryEntry],
        usage_map: Dict[str, List[UsageReference]],
    ) -> None:
        """Analyze pipeline fragment usage within a pipeline."""
        try:
            # Check if pipeline references other pipeline fragments
            fragment_refs = pipeline_config.get("fragmentRefs", [])

            for frag_ref in fragment_refs:
                for lib_id, lib in pipeline_libs.items():
                    if lib.name == frag_ref or frag_ref in lib.name:
                        usage_map[lib_id].append(
                            UsageReference(
                                library_id=lib_id,
                                referenced_in=f"pipeline:{pipeline_id}",
                                reference_type="fragment_reference",
                            )
                        )
                        lib.references.append(f"pipeline:{pipeline_id}")
                        break
        except Exception as e:
            self.log.debug(f"Error analyzing fragment usage in pipeline {pipeline_id}: {e}")

    def _extract_function_calls(self, pipeline_config: Dict[str, Any]) -> Set[str]:
        """Extract function calls from pipeline configuration."""
        functions = set()

        try:
            # Recursively search for function calls in pipeline steps
            def search_functions(obj):
                if isinstance(obj, dict):
                    # Check for function references
                    if "function" in obj:
                        func_name = obj.get("function", {}).get("name", "")
                        if func_name:
                            functions.add(func_name)

                    # Check for eval expressions that might call functions
                    if "filter" in obj and isinstance(obj["filter"], str):
                        # Simple regex to find function calls in filter expressions
                        func_calls = re.findall(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", obj["filter"])
                        functions.update(func_calls)

                    # Recurse into nested structures
                    for value in obj.values():
                        search_functions(value)

                elif isinstance(obj, list):
                    for item in obj:
                        search_functions(item)

            search_functions(pipeline_config)

        except Exception as e:
            self.log.debug(f"Error extracting function calls: {e}")

        return functions

    def _extract_lookup_references(self, pipeline_config: Dict[str, Any]) -> Set[str]:
        """Extract lookup references from pipeline configuration."""
        lookups = set()

        try:

            def search_lookups(obj):
                if isinstance(obj, dict):
                    # Check for lookup references
                    if obj.get("type") == "lookup":
                        lookup_file = obj.get("file", "")
                        if lookup_file:
                            lookups.add(lookup_file)

                    # Check for lookup function calls
                    if "function" in obj and obj.get("function", {}).get("name") == "lookup":
                        lookup_file = obj.get("function", {}).get("args", {}).get("file", "")
                        if lookup_file:
                            lookups.add(lookup_file)

                    # Recurse
                    for value in obj.values():
                        search_lookups(value)

                elif isinstance(obj, list):
                    for item in obj:
                        search_lookups(item)

            search_lookups(pipeline_config)

        except Exception as e:
            self.log.debug(f"Error extracting lookup references: {e}")

        return lookups

    def _check_unused_libraries(
        self,
        result: AnalyzerResult,
        libraries: List[LibraryEntry],
        usage_references: Dict[str, List[UsageReference]],
        client: CriblAPIClient,
    ) -> None:
        """Check for libraries that are defined but never used."""
        for lib in libraries:
            usage_count = len(usage_references.get(lib.id, []))

            if usage_count == 0:
                severity = "high" if lib.is_large else "medium"

                if lib.size_bytes > 10_000_000:  # >10MB
                    result.add_finding(
                        self.create_finding(
                            client=client,
                            id=f"massive-unused-library-{lib.id.replace(':', '-')}",
                            category="Performance",
                            severity="critical",
                            title="Massive Unused Library",
                            description=f"Library '{lib.name}' ({lib.size_bytes / 1_000_000:.1f}MB) is defined but never referenced, wasting significant memory.",
                            confidence_level="high",
                            affected_components=["memory_usage", "performance"],
                            remediation_steps=[
                                "Remove unused large libraries to free up memory and improve performance.",
                                f"Consider alternatives for the {lib.function_count} functions in '{lib.name}' if still needed.",
                            ],
                        )
                    )
                else:
                    result.add_finding(
                        self.create_finding(
                            client=client,
                            id=f"unused-library-{lib.id.replace(':', '-')}",
                            category="Maintenance",
                            severity=severity,
                            title="Unused Library Entry",
                            description=f"Library '{lib.name}' ({lib.type}) is defined but never referenced in any pipeline or route.",
                            confidence_level="high",
                            affected_components=["code_maintainability"],
                            remediation_steps=[
                                "Consider removing unused libraries to reduce maintenance overhead and potential confusion.",
                                f"Search codebase for references to '{lib.name}' before deletion.",
                            ],
                        )
                    )

    def _check_performance_impact(
        self,
        result: AnalyzerResult,
        libraries: List[LibraryEntry],
        usage_references: Dict[str, List[UsageReference]],
        client: CriblAPIClient,
    ) -> None:
        """Check for libraries that impact performance."""
        for lib in libraries:
            usage_count = len(usage_references.get(lib.id, []))
            if usage_count == 0:
                continue

            usage_frequency = usage_count  # Simplified - could be enhanced with execution frequency

            # Check for memory-inefficient libraries that are rarely used
            if lib.is_large and usage_frequency < 5:
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id=f"memory-inefficient-library-{lib.id.replace(':', '-')}",
                        category="Performance",
                        severity="high",
                        title="Memory-Inefficient Library Usage",
                        description=f"Large library '{lib.name}' ({lib.size_bytes / 1_000_000:.1f}MB) is used infrequently ({usage_count} references), wasting memory.",
                        confidence_level="high",
                        affected_components=["memory_usage", "throughput"],
                        remediation_steps=[
                            "Consider splitting large libraries into smaller, focused modules.",
                            "Optimize usage patterns to reduce memory overhead.",
                            f"Evaluate if all {lib.function_count} functions in '{lib.name}' are still needed.",
                        ],
                    )
                )

    def _check_maintenance_burden(
        self, result: AnalyzerResult, libraries: List[LibraryEntry], client: CriblAPIClient
    ) -> None:
        """Check for libraries that create maintenance burden."""
        for lib in libraries:
            if lib.has_many_functions:
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id=f"complex-maintenance-library-{lib.id.replace(':', '-')}",
                        category="Maintenance",
                        severity="medium",
                        title="Complex Library Maintenance Burden",
                        description=f"Library '{lib.name}' contains {lib.function_count} functions, creating significant maintenance overhead.",
                        confidence_level="high",
                        affected_components=["code_maintainability", "development_velocity"],
                        remediation_steps=[
                            "Consider splitting complex libraries into smaller, focused modules for easier maintenance.",
                            "Review if all functions are still needed or could be consolidated.",
                            f"Document the purpose of each of the {lib.function_count} functions in '{lib.name}'.",
                        ],
                    )
                )

    def _analyze_dependency_chains(
        self,
        result: AnalyzerResult,
        libraries: List[LibraryEntry],
        usage_references: Dict[str, List[UsageReference]],
        client: CriblAPIClient,
    ) -> None:
        """Analyze dependency chains and circular references."""
        # Build dependency graph
        dependency_graph = defaultdict(set)

        for lib in libraries:
            if lib.type == "pipeline_fragment":
                # Check what this fragment depends on
                for other_lib in libraries:
                    if other_lib.id in lib.references:
                        dependency_graph[lib.id].add(other_lib.id)

        # Check for circular dependencies (simplified check)
        visited = set()
        recursion_stack = set()

        def has_cycle(lib_id: str) -> bool:
            visited.add(lib_id)
            recursion_stack.add(lib_id)

            for dep_id in dependency_graph.get(lib_id, set()):
                if dep_id not in visited:
                    if has_cycle(dep_id):
                        return True
                elif dep_id in recursion_stack:
                    return True

            recursion_stack.remove(lib_id)
            return False

        for lib_id in dependency_graph:
            if lib_id not in visited:
                if has_cycle(lib_id):
                    result.add_finding(
                        self.create_finding(
                            client=client,
                            id=f"circular-dependency-{lib_id.replace(':', '-')}",
                            category="Architecture",
                            severity="high",
                            title="Circular Dependency Detected",
                            description=f"Library '{lib_id}' is part of a circular dependency chain, which can cause runtime issues.",
                            confidence_level="high",
                            affected_components=["runtime_stability"],
                            remediation_steps=[
                                "Refactor library dependencies to eliminate circular references.",
                                "Review library usage patterns and consolidate overlapping functionality.",
                                "Consider using a dependency injection pattern to break circular references.",
                            ],
                        )
                    )
                    break  # Only report first circular dependency found

    def _suggest_optimization_opportunities(
        self,
        result: AnalyzerResult,
        libraries: List[LibraryEntry],
        usage_references: Dict[str, List[UsageReference]],
        client: CriblAPIClient,
    ) -> None:
        """Suggest optimization opportunities."""
        # Find duplicate functionality
        name_groups = defaultdict(list)
        for lib in libraries:
            name_groups[lib.name].append(lib)

        for name, libs in name_groups.items():
            if len(libs) > 1:
                result.add_finding(
                    self.create_finding(
                        client=client,
                        id=f"duplicate-functionality-{name.replace(' ', '-').lower()}",
                        category="Optimization",
                        severity="medium",
                        title="Duplicate Library Functionality",
                        description=f"Multiple libraries share the name '{name}' ({len(libs)} instances), indicating potential duplication.",
                        confidence_level="high",
                        affected_components=["code_consistency", "resource_usage"],
                        remediation_steps=[
                            "Consolidate duplicate libraries or clarify naming conventions to avoid confusion.",
                            "Review if all instances serve different purposes or can be merged.",
                            f"Audit all {len(libs)} instances of '{name}' for consolidation opportunities.",
                        ],
                    )
                )

        # Calculate total unused library size
        total_unused_size = sum(
            lib.size_bytes for lib in libraries if len(usage_references.get(lib.id, [])) == 0
        )

        if total_unused_size > 50_000_000:  # >50MB
            result.add_finding(
                self.create_finding(
                    client=client,
                    id="significant-unused-libraries",
                    category="Optimization",
                    severity="high",
                    title="Significant Unused Library Resources",
                    description=f"Total size of unused libraries: {total_unused_size / 1_000_000:.1f}MB. Removing these could significantly improve performance.",
                    confidence_level="high",
                    affected_components=["memory_usage", "startup_time"],
                    remediation_steps=[
                        "Audit and remove unused libraries to reduce memory usage and improve startup times.",
                        f"Prioritize removal of the largest unused libraries first (potential {total_unused_size / 1_000_000:.1f}MB savings).",
                        "Test thoroughly after removal to ensure no runtime dependencies.",
                    ],
                )
            )

    def _estimate_size(self, data: Dict[str, Any]) -> int:
        """Estimate the size of a library entry in bytes."""
        try:
            # Rough estimation based on JSON string length
            return len(str(data)) * 2  # Rough multiplier for internal representation
        except:
            return 0

    def _count_functions_in_pipeline(self, pipeline_data: Dict[str, Any]) -> int:
        """Count functions in a pipeline fragment."""
        try:
            steps = pipeline_data.get("config", {}).get("steps", [])
            return len([step for step in steps if step.get("type") == "function"])
        except:
            return 0

    def _calculate_content_hash(self, data: Dict[str, Any]) -> Optional[str]:
        """Calculate a simple content hash for change detection."""
        try:
            import hashlib

            content_str = str(sorted(data.items()))
            return hashlib.md5(content_str.encode()).hexdigest()[:8]
        except:
            return None
