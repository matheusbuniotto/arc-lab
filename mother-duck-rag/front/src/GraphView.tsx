import { useCallback, useRef, useState, useEffect } from "react";
import ForceGraph2D from "react-force-graph-2d";
import type { GraphData, GraphNode } from "./api";

type GraphViewProps = {
  data: GraphData | null;
  onNodeClick?: (node: GraphNode) => void;
};

export function GraphView({ data, onNodeClick }: GraphViewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dim, setDim] = useState({ w: 800, h: 600 });

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const update = () => {
      const r = el.getBoundingClientRect();
      if (r.width && r.height) setDim({ w: r.width, h: r.height });
    };
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // Force-graph expects links with source/target as node objects; API gives slugs
  const graphData = data
    ? (() => {
        const nodeMap = new Map<string | undefined, GraphNode>();
        data.nodes.forEach((n) => nodeMap.set(n.id, n));
        const nodes = data.nodes;
        const links: { source: GraphNode; target: GraphNode }[] = [];
        data.links.forEach((l) => {
          const src = nodeMap.get(l.source);
          const tgt = nodeMap.get(l.target);
          if (src && tgt) links.push({ source: src, target: tgt });
        });
        return { nodes, links };
      })()
    : { nodes: [], links: [] };

  const handleNodeClick = useCallback(
    (node: { id?: string; slug?: string; title?: string }) => {
      const n = node as GraphNode;
      if (n && (n.id ?? n.slug) && onNodeClick) onNodeClick(n);
    },
    [onNodeClick]
  );

  if (!data || (data.nodes.length === 0 && data.links.length === 0)) {
    return (
      <div className="graph-container" style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
        <span className="muted">No graph data. Ingest a vault with wikilinks.</span>
      </div>
    );
  }

  return (
    <div ref={containerRef} className="graph-container">
      <ForceGraph2D
        graphData={graphData}
        width={dim.w}
        height={dim.h}
        nodeId="id"
        nodeLabel={(n) => (n as GraphNode).title ?? (n as GraphNode).slug ?? ""}
        nodeCanvasObject={(node, ctx, globalScale) => {
          const n = node as GraphNode;
          const label = n.title ?? n.slug ?? "";
          const fontSize = 12 / globalScale;
          ctx.font = `${fontSize}px ${getComputedStyle(document.body).fontFamily}`;
          ctx.textAlign = "center";
          ctx.textBaseline = "middle";
          ctx.fillStyle = "rgba(204, 204, 204, 0.95)";
          ctx.fillText(label, node.x ?? 0, node.y ?? 0);
        }}
        linkColor={() => "rgba(124, 107, 220, 0.4)"}
        linkWidth={1}
        linkDirectionalArrowLength={4}
        linkDirectionalArrowRelPos={1}
        onNodeClick={handleNodeClick}
        backgroundColor="#0c0c0f"
      />
      <div className="graph-legend">Drag to pan · Scroll to zoom · Click node to focus</div>
    </div>
  );
}
