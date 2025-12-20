Architecture Design Document: Automated EDA Artifact Generation SaaS Backend1. Executive Summary and Strategic Vision1.1. Project Context and Technical ImperativeThe Electronic Design Automation (EDA) industry currently faces a significant bottleneck in the hardware design lifecycle: the manual transcription of component specifications from static PDF datasheets into executable design artifacts. Engineers spend countless hours deciphering "Typical Application" schematics, extracting tabular electrical characteristics, and solving feedback loop equations to select passive components. This manual process is prone to human error, specifically in the calculation of critical values such as feedback resistors ($R_{fb}$) and compensation networks, which directly impact the stability and efficiency of power management integrated circuits (PMICs).We are tasked with architecting a SaaS backend that automates this workflow. The system transforms a raw PDF datasheet (e.g., a Texas Instruments Step-Down Converter) into a fully validated KiCad schematic and a calculated Bill of Materials (BOM).1.2. The Core Technical Constraint: The "Math Gap"A defining constraint of this architecture is the unreliability of Large Language Models (LLMs) in performing precise arithmetic and algebraic solving. While LLMs excel at semantic extraction and reasoning, they suffer from "hallucination" when tasked with numerical computation. Predicting that "R1 is 10k Ohms" based on probabilistic token generation is unacceptable in hardware design, where a 10% deviation can lead to catastrophic circuit failure.Consequently, this architecture rejects the "Direct Answer" pattern in favor of a "Code Interpreter" / "Tool Use" pattern. The LLM’s role is shifted from calculator to engineer: it identifies the problem, formulates the mathematical model (equations), extracts the boundary conditions (datasheet constants), and writes executable Python code to solve for the unknowns.1.3. Architectural Solution: The Cyclic Multi-Agent GraphTo implement this sophisticated reasoning chain, we adopt a Cyclic, Stateful Multi-Agent Architecture powered by LangGraph. Unlike linear "Chain-of-Thought" workflows, a cyclic graph allows for iterative error correction and human-in-the-loop (HITL) intervention. If a required variable is missing, the system does not fail; it loops back to query the user or re-scan the document.This document outlines the comprehensive implementation plan, adhering to a strict "2025/2026" Backend Coding Standard that prioritizes type safety, asynchronous concurrency, and observability.2. Part 1: The LangGraph Orchestration ("The Brain")The orchestration layer is the cognitive core of the application. We utilize LangGraph to model the datasheet-to-design workflow as a state machine. This approach allows us to define rigid interfaces between agents while permitting flexible, non-deterministic execution paths required for complex problem solving.2.1. Architectural Philosophy: Why Cyclic Graphs?In a linear chain (DAG), the output of one step is piped to the next. If the "Equation Extractor" fails to find a variable required by the "Math Engineer," the chain breaks. In a cyclic graph, the "Math Engineer" can signal a MissingVariable state, triggering a transition back to the "Constants Miner" to look specifically for that variable, or to a "Human-in-the-Loop" node to request user input. This resilience is critical for processing diverse datasheet formats.2.2. GraphState Definition (Pydantic V2)The GraphState serves as the shared memory or "blackboard" for all agents. To ensure rigorous type safety across agent boundaries, we define the state using Pydantic V2. This enforces data validation at runtime, preventing the common "garbage-in, garbage-out" issues prevalent in untyped Python dictionaries.Pythonfrom typing import List, Dict, Optional, Any, Union, Annotated
from pydantic import BaseModel, Field, HttpUrl
import operator

# Reducer function to allow agents to append messages to the history
def merge_messages(left: List[Any], right: List[Any]) -> List[Any]:
    return left + right

class PDFChunk(BaseModel):
    """Represents a semantic segment of the datasheet."""
    content: str
    page_number: int
    section_title: Optional[str] = None

class ExtractedConstant(BaseModel):
    """Represents a fixed value found in tables."""
    name: str = Field(..., description="Standardized name, e.g., 'V_ref'")
    value: float
    unit: str
    source_context: str = Field(..., description="Snippet verifying the extraction")

class ExtractedEquation(BaseModel):
    """Represents a design formula found in text."""
    target_variable: str # e.g., "R1"
    latex_raw: str       # e.g., "R_1 = R_2 \times (V_{out}/V_{ref} - 1)"
    python_code: str     # e.g., "R1 = R2 * (V_out / V_ref - 1)"
    dependencies: List[str] # e.g.,

class Component(BaseModel):
    """Represents a node in the Abstract Netlist."""
    ref_des: str # e.g., "U1"
    value: str   # e.g., "TPS62125" or "10uF"
    pins: Dict[str, str] # e.g., {"1": "VIN", "2": "GND"}
    footprint: Optional[str] = None

class GraphState(BaseModel):
    """
    The Single Source of Truth for the LangGraph workflow.
    """
    # 1. Raw Ingestion Artifacts
    pdf_chunks: List = Field(default_factory=list)
    schematic_image_path: Optional[str] = None
    
    # 2. Extracted Knowledge (The "Context")
    extracted_constants: Dict[str, ExtractedConstant] = Field(
        default_factory=dict,
        description="Map of standard names to extracted values"
    )
    design_equations: List[ExtractedEquation] = Field(
        default_factory=list,
        description="All formulas extracted from Application Information"
    )
    
    # 3. User Constraints & Interaction (The "Requirements")
    user_inputs: Dict[str, float] = Field(
        default_factory=dict,
        description="User-defined constraints, e.g., {'V_out': 5.0}"
    )
    missing_variables: List[str] = Field(
        default_factory=list,
        description="Variables preventing equation solution"
    )
    
    # 4. Topology & Output (The "Design")
    netlist_topology: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Adjacency list representation of the circuit"
    )
    abstract_netlist: List[Component] = Field(default_factory=list)
    calculated_bom: Dict[str, float] = Field(
        default_factory=dict,
        description="Final computed values for passives"
    )
    
    # 5. Graph Control State
    messages: Annotated[List[Any], merge_messages]
    next_node: Optional[str] = None
    error_log: List[str] = Field(default_factory=list)
2.3. Node Definitions and Agent LogicThe architecture decomposes the transcription task into seven distinct cognitive nodes. Each node uses a specific LLM prompt strategy and toolset.Node A: Ingestion SupervisorRole: The Router.The Ingestion Supervisor is the entry point. It receives the semantically filtered content (discussed in Part 2). Its primary responsibility is not extraction, but routing strategy.Logic: It scans the input chunks for visual markers (references to Figure X) versus tabular markers (Electrical Characteristics).Decision:If a reference design schematic is detected (via metadata from the PDF parser), it routes to the Vision Agent.Simultaneously, it routes text chunks containing tables to the Constants Miner.It routes text chunks containing prose to the Equation Extractor.Orchestration: This node utilizes the "Supervisor" pattern described in research snippet 1, managing parallel execution branches to minimize total latency.Node B: Vision Agent (Multimodal)Role: The Topology Mapper.This agent is responsible for converting a raster image of the schematic into a structured netlist.Model: GPT-4o or Claude-3.5-Vision. Research snippet 2 indicates that vision-language models (VLMs) are increasingly capable of this, but require specific prompting to avoid hallucinations.Process:Preprocessing: The image is converted to high-contrast grayscale to enhance pin numbers and labels.Prompting: The prompt instructs the VLM to act as a "Netlist Extractor." It must list every component, its Reference Designator (e.g., R1, C1), and exactly which nets (wires) connect to its pins.Normalization: The output is parsed into the Component Pydantic model. If the VLM identifies a resistor as "Resistor connected to pin 3," the agent assigns a temporary ID (e.g., R_Unknown_1) and flags it for reconciliation with the calculated_bom later.Output: Updates netlist_topology and abstract_netlist in GraphState.Node C: Constants MinerRole: The Fact Retriever.This agent focuses on the "Electrical Characteristics" tables.Challenge: PDF tables are often multi-column or span across pages. Simple text extraction destroys row alignment.Strategy: We employ a specialized "Table-to-JSON" tool (using the gmft or unstructured library) before passing data to the LLM.Logic: The LLM receives the JSON representation of the table. It is prompted with a schema of "Standard Variables" (e.g., V_ref, I_sw_limit, V_uvlo). It must scan the rows for synonyms (e.g., "Feedback Voltage" $\rightarrow$ V_ref) and extract the "Typical" value.Validation: It performs a unit check. If the column header says "mV" and the value is "600", it must convert to "0.6" Volts to maintain SI unit consistency in the extracted_constants map.Node D: Equation ExtractorRole: The Mathematician (Formulator).This agent scans the "Application Information" section.Logic: It looks for patterns indicating design procedures. For a Buck Converter, it seeks the formula for the feedback divider network.Extraction: It extracts the raw LaTeX string and attempts to convert it to a Python lambda string.Context Awareness: It must capture the surrounding text to define the variables. If the text says "Where R1 is the high-side resistor," this mapping is crucial for the Math Engineer.Node E: The "Math Engineer" (Code Generator)Role: The Python Developer.This is the Core Technical Constraint solver. This agent does not calculate. It writes code.Input: It reads extracted_constants (e.g., $V_{ref}=0.8$), user_inputs (e.g., $V_{out}=3.3$), and design_equations.Reasoning:Constructs a dependency graph. To solve for $R_2$, do I have $R_1$, $V_{out}$, and $V_{ref}$?If $R_1$ is a free variable (common in feedback dividers), the agent writes code to select a standard value (e.g., $10k\Omega$) and then solves for $R_2$.Missing Data Check: If the equation requires L_target (Inductance) but the user hasn't provided it, the Math Engineer stops code generation and updates GraphState.missing_variables. It then transitions the graph to the HITL Node.Output: A complete, self-contained Python script.Node F: The "Executor" (Tool Node)Role: The Sandbox.Implementation: This node executes the script from the Math Engineer.Security: As highlighted in 3 and 4, executing LLM-generated code locally is a security risk. We utilize E2B (E2B Code Interpreter) for secure, ephemeral sandboxing.Process:Instantiates an E2B sandbox session.Uploads the script.Executes and captures stdout.Parses the JSON result from stdout (e.g., {"R1": 10000, "R2": 32400}).Updates calculated_bom in the state.Node G: Human-in-the-Loop NodeRole: The Interrupter.Logic: If the graph transitions here (from Math Engineer), it triggers a LangGraph Interrupt (5).State Persistence: The current GraphState is saved to the Postgres checkpointer.API Response: The HTTP request handling the initial job returns a specific status code (e.g., 202 Accepted or a custom 422 Input Required) with the list of missing_variables.Resume: When the user calls the /resume endpoint with the missing data, the graph restores state, updates user_inputs, and transitions back to the Math Engineer.3. Part 2: Data Ingestion & Chunking StrategyHandling 60-page datasheets with multi-column scientific layouts is a non-trivial engineering challenge. Standard text extraction often yields "garbage" when faced with complex layouts, leading to poor LLM performance.3.1. PDF Parsing Stack: The Scientific Layout ChallengeWe evaluated three primary approaches based on research snippets 7, and 9:FeatureUnstructuredPyMuPDF (fitz)Marker (marker-pdf)SpeedSlow (OCR heavy)Blazing FastModerate (Model inference)Multi-column SupportGood (Layout analysis)Poor (Linear text stream)Excellent (Trained for it)Equation ExtractionWeakNone (Raw characters)Excellent (LaTeX conversion)Table ExtractionModerateBasicGood (Markdown tables)RecommendationFallbackMetadata/Images onlyPrimary EngineSelected Stack: Marker (marker-pdf)We select Marker as the primary parsing engine. Unlike traditional OCR, Marker uses a multimodal model pipeline specifically trained on scientific papers and textbooks. It excels at identifying reading order in multi-column layouts and, crucially, converts mathematical formulas directly into LaTeX format. This aligns perfectly with our need to extract design_equations.Fallback: If Marker fails (low confidence score), we fall back to Unstructured, which uses Tesseract OCR and LayoutLM models for robust but slower extraction. PyMuPDF is retained solely for identifying and cropping the schematic_image_path since it allows precise coordinate-based image extraction.3.2. Semantic Routing: The "Needle in a Haystack"Processing the entire PDF (often 60+ pages) wastes tokens and introduces noise (e.g., "Tape and Reel Information" or "Package Dimensions"). We must route the LLM only to relevant sections.Strategy: Two-Stage Semantic FilteringStage 1: Heuristic Keyword Filtering (The Fast Pass)We parse the Table of Contents (TOC) if available.We scan page headers/footers for high-value keywords: ``.This reduces the document from 60 pages to ~10 high-probability pages.Stage 2: Embedding-Based Vector Routing (The Smart Pass)We utilize OpenAI's text-embedding-3-small to generate vectors for the candidate pages.We compare these vectors against a pre-computed "Anchor Set" of embeddings derived from known "Golden Datasheets" (e.g., embeddings of the Application Information section of a standard TI datasheet).Snippet Insight: Research snippet 10 and 11 suggest that semantic routing significantly improves RAG performance by filtering irrelevant context.Thresholding: Only chunks with a cosine similarity > 0.75 are passed to the LangGraph agents.3.3. Chunking Strategy: Context PreservationStandard fixed-size chunking (e.g., 500 characters) is disastrous for equations, often splitting the formula ($V_{out} =...$) from the variable definitions ($Where V_{out} is...$).Selected Strategy: Semantic ChunkingWe implement the Semantic Chunking strategy described in 12 and.13Sentence Splitting: The text is first split into sentences.Semantic Coherence: We calculate the cosine distance between the embeddings of adjacent sentences.Boundary Detection: If the distance exceeds a threshold (indicating a shift in topic), a chunk boundary is created.Result: This ensures that a "Design Procedure" paragraph and its associated equations remain in the same chunk, providing the EquationExtractor with complete context.4. Part 3: The API Architecture (FastAPI + Async)The interactive nature of the application (HITL) and the long latency of LLM chains necessitate a fully asynchronous API architecture.4.1. Asynchronous Design PrinciplesWe utilize FastAPI running on an ASGI server (Uvicorn). All database interactions and LLM calls are await-ed to ensure the event loop remains non-blocking. This allows a single server instance to handle hundreds of concurrent datasheet processing jobs.4.2. Endpoint Definition1. POST /analyzeInitiates the datasheet processing job.Request: multipart/form-data with the PDF file and a JSON string for user_constraints.Behavior:Persists the uploaded PDF to object storage (S3/MinIO).Creates a Job record in PostgreSQL with status PENDING.Initializes the GraphState with the file path.Dispatches the LangGraph execution to a background worker (via Celery or Redis Queue) to decouple processing from the HTTP response.Response: 202 Accepted containing a job_id.2. GET /jobs/{job_id}/stream (SSE)Provides real-time visibility into the "Brain's" thinking process.Technology: Server-Sent Events (SSE). As noted in 14 and 15, SSE is superior to WebSockets for unidirectional status updates due to simpler protocol overhead and better firewall traversal.Implementation:The endpoint yields a generator that subscribes to the LangGraph event stream (graph.astream_events).Events are formatted as structured JSON messages:JSONevent: agent_update
data: {
  "node": "ConstantsMiner",
  "status": "extracting",
  "message": "Found V_ref = 0.8V in Table 3."
}
Interrupt Handling: If the graph hits the HITL node, an event of type interrupt is sent, prompting the frontend to display a form for the missing variables.3. POST /jobs/{job_id}/resumeHandles user input for HITL scenarios.Payload: {"missing_variables": {"L_target": 2.2e-6}}.Behavior:Retrieves the suspended graph state from the checkpointer using job_id as the thread ID.Updates the state with the provided values.Commands the graph to resume execution (6).4.3. Final JSON Payload SchemaThe frontend receives this payload to render the interactive BOM and download the KiCad files.JSON{
  "job_id": "uuid",
  "status": "COMPLETED",
  "metadata": {
    "device_name": "TPS62125",
    "datasheet_title": "3V-17V Step-Down Converter"
  },
  "design_parameters": {
    "V_in": 12.0,
    "V_out": 3.3,
    "I_out_max": 0.5
  },
  "circuit_design": {
    "schematic_nodes":},
      {"ref": "R1", "lib": "R", "value": "100k", "pos": },
      {"ref": "R2", "lib": "R", "value": "32.4k", "pos": }
    ],
    "nets":},
      {"name": "VOUT", "connections":}
    ]
  },
  "bom":,
  "download_links": {
    "kicad_sch": "/jobs/{job_id}/artifacts/schematic.kicad_sch"
  }
}
5. Part 4: KiCad S-Expression GenerationThe final artifact is a .kicad_sch file. KiCad 6.0+ uses a Lisp-based S-Expression format. Generating this programmatically requires strict adherence to the file format specification (16).5.1. Generation Strategy: The "Abstract to Concrete" BridgeThe Vision Agent provides an Abstract Netlist (topology), and the Math Engineer provides the Values. The KiCad Generator must merge these and add Spatial Geometry.Symbol Mapping: We maintain a mapping database of generic symbols (Device:R, Device:C, Device:L). For the specific IC, we generate a "rectangle symbol" on the fly using KiCad's symbol library format, creating pins based on the netlist data.Auto-Placement: We use networkx to model the netlist as a graph. We apply a planar layout algorithm or a force-directed layout to determine relative $(x, y)$ coordinates for components, ensuring that the FB (Feedback) network is visually close to the FB pin of the IC.UUID Generation: KiCad 7+ requires every symbol and pin to have a unique UUID. We use Python's uuid library to generate these deterministically based on the reference designator to ensure file stability across regenerations.5.2. Python Implementation SnippetBelow is a robust implementation for generating a Resistor S-Expression. This code adheres to the grammar defined in 16 and.17Pythonimport uuid

def create_kicad_resistor(
    ref_des: str, 
    value: str, 
    x_pos: float, 
    y_pos: float, 
    rotation: int = 0
) -> str:
    """
    Generates a KiCad 7.0+ S-Expression string for a resistor component.
    
    Args:
        ref_des (str): Reference Designator, e.g., "R1"
        value (str): Component Value, e.g., "10k"
        x_pos, y_pos (float): Coordinates in mm.
        rotation (int): Rotation in degrees (0, 90, 180, 270).
        
    Returns:
        str: Formatted S-Expression block.
    """
    # Deterministic UUID generation for reproducibility
    # Using specific namespace ensures R1 always gets the same UUID if re-generated
    comp_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, f"{ref_des}_{value}")
    
    # KiCad uses 'at' for position: (at x y rotation)
    at_expr = f"(at {x_pos:.2f} {y_pos:.2f} {rotation})"
    
    # Text effects for visibility
    font_effects = "(effects (font (size 1.27 1.27)) (justify left))"
    
    # S-Expression Template
    # lib_id "Device:R" is the standard KiCad library reference for a resistor
    sexpr = f"""
    (symbol (lib_id "Device:R") {at_expr} (unit 1)
      (in_bom yes) (on_board yes) (dnp no)
      (uuid "{str(comp_uuid)}")
      (property "Reference" "{ref_des}" (at {x_pos:.2f} {y_pos-2.54:.2f} 0)
        {font_effects}
      )
      (property "Value" "{value}" (at {x_pos:.2f} {y_pos+2.54:.2f} 0)
        {font_effects}
      )
      (property "Footprint" "Resistor_SMD:R_0603_1608Metric" (at {x_pos:.2f} {y_pos:.2f} 0)
        (effects (font (size 1.27 1.27)) hide)
      )
      ;; Pins must also have UUIDs. We generate them derived from the component UUID.
      (pin "1" (uuid "{uuid.uuid5(comp_uuid, 'pin1')}"))
      (pin "2" (uuid "{uuid.uuid5(comp_uuid, 'pin2')}"))
    )
    """
    return sexpr.strip()

# Example Usage
print(create_kicad_resistor("R_FB1", "49.9k", 120.0, 85.5, 90))
6. Part 5: The "2025/2026 Backend Coding Standard"To ensure the longevity and maintainability of this complex multi-agent system, we enforce a rigorous coding standard. This is not merely a style guide but a set of architectural mandates.6.1. Type Safety & Validation (Pydantic V2)Mandate: Dynamic typing is forbidden for data exchange. All API inputs, database models, and LLM structured outputs must use Pydantic V2.Static Analysis: The CI pipeline will run mypy or pyright in strict mode.Reasoning: Pydantic V2 (written in Rust) offers significant performance improvements and validation correctness over V1. It acts as the "contract" between the deterministic code and the probabilistic LLM output.6.2. Asynchronous ConcurrencyMandate: All I/O-bound operations must be async.Rationale: The application is I/O heavy (PDF uploads, DB reads, external LLM API calls). Blocking code in the main thread is unacceptable.Framework: We use httpx for async HTTP client calls instead of requests.6.3. Observability: Structured LoggingTool: structlog.Philosophy: Logs are data, not text.Requirement: All logs must be emitted as JSON. Every request must be tagged with a trace_id (propagated via OpenTelemetry headers) to allow tracing a request from the API entry point, through the LangGraph nodes, to the E2B sandbox execution.Implementation:Pythonimport structlog
log = structlog.get_logger()

# BAD
log.info(f"Processing chunk {chunk_id}")

# GOOD
await log.ainfo("processing_chunk", chunk_id=chunk_id, page=5, confidence_score=0.92)
6.4. Testing: Mocking the StochasticChallenge: Testing LLM applications is expensive and non-deterministic.Solution: We mandate Record/Replay Testing using vcr.py or pytest-recording.Process:Run the test suite once against the live OpenAI API. vcr.py records the HTTP interactions to a "cassette" (YAML file).In CI/CD, the tests run against the cassette. This ensures determinism and zero cost.Unit Tests: Use pytest-asyncio for all async components.6.5. Linting & FormattingTool: Ruff.Rationale: Ruff replaces the fragmented ecosystem of Black, Isort, and Flake8 with a single, ultra-fast Rust-based tool.Configuration:Ini, TOML# pyproject.toml
[tool.ruff]
line-length = 100
target-version = "py311"
[tool.ruff.lint]
select = # Enforce strict rules
6.6. Error HandlingPolicy: Zero 500 Errors.Implementation: A global exception handler middleware must intercept all errors.PDFParsingError -> 422 Unprocessable EntityLLMContextLimitError -> 503 Service UnavailableMissingVariableError -> Custom 400 Bad Request with missing_vars payload.7. ConclusionThis architecture represents a paradigm shift in EDA tooling. By acknowledging the limitations of LLMs and wrapping them in a robust LangGraph orchestration with Code Interpreter capabilities, we bridge the gap between unstructured text and rigorous engineering design. The use of Marker for ingestion, E2B for secure execution, and KiCad S-Expressions for output ensures that the system is not just a "demo" but a production-grade engineering assistant. The strict adherence to modern coding standards ensures that this "Brain" remains maintainable as it evolves to handle increasingly complex integrated circuits.