/**
 * TreemapChart Component
 *
 * D3 treemap showing grouped spend data. Responsive.
 * Click on a cell drills down (calls onDrillDown callback).
 */

import { useRef, useEffect } from 'react';
import * as d3 from 'd3';
import type { TreemapNode } from '../types';
import { formatCompact } from '../utils';

interface TreemapChartProps {
  data: TreemapNode | null;
  width?: number;
  height?: number;
  onDrillDown?: (name: string) => void;
}

const COLORS = [
  '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6',
  '#ec4899', '#06b6d4', '#84cc16', '#f97316', '#6366f1',
];

export default function TreemapChart({
  data,
  width = 800,
  height = 400,
  onDrillDown,
}: TreemapChartProps) {
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!svgRef.current || !data || !data.children?.length) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const root = d3
      .hierarchy(data)
      .sum((d) => (d.children ? 0 : d.value))
      .sort((a, b) => (b.value ?? 0) - (a.value ?? 0));

    const treemapRoot = d3.treemap<TreemapNode>().size([width, height]).padding(2).round(true)(root);

    const leaves = treemapRoot.leaves();

    const cell = svg
      .selectAll<SVGGElement, d3.HierarchyRectangularNode<TreemapNode>>('g')
      .data(leaves)
      .join('g')
      .attr('transform', (d) => `translate(${d.x0},${d.y0})`);

    cell
      .append('rect')
      .attr('width', (d) => d.x1 - d.x0)
      .attr('height', (d) => d.y1 - d.y0)
      .attr('fill', (_d, i) => COLORS[i % COLORS.length])
      .attr('rx', 2)
      .attr('class', 'cursor-pointer opacity-90 hover:opacity-100')
      .on('click', (_e, d) => {
        if (onDrillDown && d.data.name) onDrillDown(d.data.name);
      });

    cell
      .append('text')
      .attr('x', 4)
      .attr('y', 16)
      .attr('fill', 'white')
      .attr('font-size', '12px')
      .attr('font-weight', '600')
      .text((d) => {
        const w = d.x1 - d.x0;
        return w > 60 ? d.data.name : '';
      });

    cell
      .append('text')
      .attr('x', 4)
      .attr('y', 30)
      .attr('fill', 'rgba(255,255,255,0.8)')
      .attr('font-size', '11px')
      .text((d) => {
        const w = d.x1 - d.x0;
        return w > 80 ? formatCompact(d.data.value) : '';
      });
  }, [data, width, height, onDrillDown]);

  if (!data || !data.children?.length) {
    return <div data-testid="treemap-chart" className="text-gray-400 text-sm p-4" role="status">No data for treemap</div>;
  }

  return (
    <div data-testid="treemap-chart">
      <svg ref={svgRef} width={width} height={height} role="img" aria-label="Treemap chart of spending distribution">
        <title>Spending distribution by category</title>
      </svg>
    </div>
  );
}
