import logging
import cv2
import numpy as np
import networkx as nx
from pathlib import Path
from typing import List, Tuple
from uuid import uuid4
from wireframe.agents.state import ComponentDict, NetDict, ExtractedCircuitBase

# Placeholder for deep learning libraries
try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None

logger = logging.getLogger(__name__)

class SchematicExtractionService:
    def __init__(self, model_path: str = "yolo11n.pt"):
        """
        Initializes the computer vision models.
        In production, model_path would point to your fine-tuned weights.
        """
        self.component_model = YOLO(model_path) if YOLO else None
        # self.wire_model = ... # Load DT-LSD model here
        
    def process_schematic(self, image_bytes: bytes) -> ExtractedCircuitBase:
        """
        Main pipeline entry point corresponding to Section 7.1 of the report.
        """
        # 1. Pre-processing (Convert bytes to CV2 image)
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # 2. Component Detection (Stage 3: Tiling + YOLO)
        components = self._detect_components_tiled(image)
        
        # 3. Wire/Topology Extraction (Stage 4: Vectorization)
        # Note: In a real implementation, this calls DT-LSD. 
        # Here we mock segments for demonstration or use morphological fallback.
        segments = self._extract_wire_segments(image)
        
        # 4. Junction Detection
        junctions = self._detect_junctions(image, components)
        
        # 5. Graph Construction (Stage 5: Logic Layer)
        netlist = self._build_topology_graph(components, segments, junctions)
        
        return {
            "components": components,
            "netlist": netlist
        }

    def _detect_components_tiled(self, image: np.ndarray, tile_size: int = 1024, overlap: float = 0.2) -> List[ComponentDict]:
        """
        Implements the Tiling Strategy (Section 3.1.1) to detect small components.
        """
        if not self.component_model:
            logger.warning("YOLO model not loaded. Returning empty components.")
            return []

        height, width = image.shape[:2]
        step = int(tile_size * (1 - overlap))
        
        all_detections = []

        for y in range(0, height, step):
            for x in range(0, width, step):
                # Handle edge cases
                h_tile = min(tile_size, height - y)
                w_tile = min(tile_size, width - x)
                
                tile = image[y:y+h_tile, x:x+w_tile]
                
                # Run Inference
                results = self.component_model(tile, verbose=False)
                
                # Map coordinates back to global frame
                for r in results:
                    for box in r.boxes:
                        b = box.xyxy[0].cpu().numpy() # local coordinates
                        global_box = [
                            b[0] + x, b[1] + y,
                            b[2] + x, b[3] + y
                        ]
                        cls_id = int(box.cls[0])
                        conf = float(box.conf[0])
                        
                        all_detections.append({
                            "bbox": global_box,
                            "class": self.component_model.names[cls_id],
                            "confidence": conf,
                            "id": str(uuid4())[:8]
                        })

        # Apply Non-Maximum Suppression (NMS) to merge overlapping detections from tiles
        return self._apply_global_nms(all_detections)

    def _apply_global_nms(self, detections: List[ComponentDict], iou_thresh: float = 0.5) -> List[ComponentDict]:
        """Simple NMS implementation for merged tiles."""
        if not detections:
            return []
            
        # Sort by confidence
        detections = sorted(detections, key=lambda x: x['confidence'], reverse=True)
        keep = []
        
        while detections:
            current = detections.pop(0)
            keep.append(current)
            
            # Remove detections that overlap significantly
            detections = [
                d for d in detections 
                if self._iou(current['bbox'], d['bbox']) < iou_thresh
            ]
            
        return keep

    def _iou(self, boxA, boxB):
        # Determine the (x, y)-coordinates of the intersection rectangle
        xA = max(boxA[0], boxB[0])
        yA = max(boxA[1], boxB[1])
        xB = min(boxA[2], boxB[2])
        yB = min(boxA[3], boxB[3])
        interArea = max(0, xB - xA) * max(0, yB - yA)
        boxAArea = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
        boxBArea = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])
        return interArea / float(boxAArea + boxBArea - interArea)

    def _extract_wire_segments(self, image: np.ndarray) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
        """
        Placeholder for DT-LSD (Deformable Transformer for Line Segment Detection).
        For now, this uses LSD (Line Segment Detector) from OpenCV as a fallback.
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        lsd = cv2.createLineSegmentDetector(0)
        lines, _, _, _ = lsd.detect(gray)
        
        segments = []
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = map(int, line[0])
                # Filter out extremely short lines (noise)
                if np.hypot(x2-x1, y2-y1) > 10: 
                    segments.append(((x1, y1), (x2, y2)))
        return segments

    def _detect_junctions(self, image: np.ndarray, components: List[ComponentDict]) -> List[Tuple[int, int]]:
        """
        Detects junction dots. 
        In the report (Section 4.2), this is crucial for the 'Junction vs Crossover' logic.
        """
        # In a real pipeline, 'dot' would be a class in YOLO.
        # Here we look for detections labeled 'junction' or 'dot'
        junctions = []
        for c in components:
            if c['class'] in ['junction', 'dot', 'connection_dot']:
                cx = (c['bbox'][0] + c['bbox'][2]) / 2
                cy = (c['bbox'][1] + c['bbox'][3]) / 2
                junctions.append((int(cx), int(cy)))
        return junctions

    def _build_topology_graph(self, components: List[ComponentDict], segments: List[Tuple[Tuple[int, int], Tuple[int, int]]], junctions: List[Tuple[int, int]]) -> List[NetDict]:
        """
        Implements the 'Image2Net' Heuristic Logic (Section 4.2).
        Constructs a graph where nodes are intersection points and edges are wires.
        """
        G = nx.Graph()
        
        # 1. Add all wire segments to graph
        # We need to snap endpoints that are close to each other
        snap_threshold = 15.0 # pixels
        
        def get_node_key(pt):
            # Quantize/Snap coordinates to merge close points
            return (round(pt[0] / snap_threshold) * snap_threshold, 
                    round(pt[1] / snap_threshold) * snap_threshold)

        for p1, p2 in segments:
            n1 = get_node_key(p1)
            n2 = get_node_key(p2)
            if n1 != n2:
                G.add_edge(n1, n2, weight=np.hypot(p1[0]-p2[0], p1[1]-p2[1]))

        # 2. Associate Components with Graph Nodes
        component_nodes = {}
        for comp in components:
            # Find nearest graph node to the component boundary (simplified Pin mapping)
            center = ((comp['bbox'][0]+comp['bbox'][2])/2, (comp['bbox'][1]+comp['bbox'][3])/2)
            
            # Find closest node in G to this component center
            if len(G.nodes) > 0:
                nearest_node = min(G.nodes, key=lambda n: np.hypot(n[0]-center[0], n[1]-center[1]))
                dist = np.hypot(nearest_node[0]-center[0], nearest_node[1]-center[1])
                
                # If close enough, associate
                if dist < 100: # Threshold depends on component size
                    component_nodes[comp['id']] = nearest_node
                    # Tag the node in the graph
                    nx.set_node_attributes(G, {nearest_node: {"component_id": comp['id']}})

        # 3. Resolve Junctions vs Crossovers (Section 4.2)
        # Iterate over high-degree nodes
        nodes_to_process = [n for n, d in G.degree() if d >= 3]
        
        for node in nodes_to_process:
            degree = G.degree[node]
            is_junction = False
            
            # Check if this node is spatially close to a detected "Junction Dot"
            for j in junctions:
                if np.hypot(node[0]-j[0], node[1]-j[1]) < snap_threshold:
                    is_junction = True
                    break
            
            if is_junction:
                # Rule 1: Dot -> Keep as electrical node (Net merge)
                pass 
            elif degree == 4:
                # Rule 2: No Dot + 4-way -> Crossover. 
                # We need to split this node into two disconnected paths (Vertical and Horizontal)
                neighbors = list(G.neighbors(node))
                # Sort neighbors by angle or x/y to find collinear pairs
                # Simplified: connect collinear neighbors and remove central node
                pass # Implementation of node splitting logic
            elif degree == 3:
                # Rule 3: No Dot + 3-way -> Implicit Junction (T-junction)
                pass

        # 4. Traverse Graph to Extract Nets
        nets = []
        visited_nodes = set()
        
        for component_id, start_node in component_nodes.items():
            if start_node in visited_nodes:
                continue
                
            # Find all connected nodes (BFS/DFS) representing one electrical net
            if start_node in G:
                electrical_net_nodes = list(nx.node_connected_component(G, start_node))
                
                # Find all components attached to this net
                attached_components = []
                for node in electrical_net_nodes:
                    visited_nodes.add(node)
                    if "component_id" in G.nodes[node]:
                        attached_components.append(G.nodes[node]["component_id"])
                
                if len(attached_components) > 1:
                    nets.append({
                        "net_id": str(uuid4())[:8],
                        "connected_components": list(set(attached_components))
                    })
                
        return nets