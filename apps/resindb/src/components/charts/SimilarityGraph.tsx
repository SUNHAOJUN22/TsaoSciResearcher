import React, { useMemo } from 'react';
import type { EChartsOption } from '@/lib/echarts';
import type { SimilarityNode, SimilarityEdge } from '@/workers/similarityWorker';
import { ScientificEChart } from './ScientificEChart';
import { escapeScientificHtml, formatScientificNumber, scientificTooltipItem } from './scientificFigurePolicy';

interface SimilarityGraphProps { nodes: SimilarityNode[]; edges: SimilarityEdge[]; theme: 'light' | 'dark' }

export const SimilarityGraph: React.FC<SimilarityGraphProps> = React.memo(({ nodes, edges, theme }) => {
  const option = useMemo<EChartsOption>(() => {
    const categories = Array.from(new Set(nodes.map((node) => node.category))).map((name) => ({ name }));
    return {
      title: { text: 'Overlap-adjusted similarity network', subtext: 'Edges encode standardized-feature cosine similarity multiplied by shared-feature coverage. Network proximity is descriptive and does not imply chemical identity.', left: 'center', top: 6, textStyle: { fontSize: 14, fontWeight: 650 }, subtextStyle: { fontSize: 10 } },
      legend: { bottom: 4, data: categories.map((entry) => entry.name) },
      tooltip: { formatter: (params: unknown) => {
        const item = scientificTooltipItem(params);
        if (item?.dataType === 'node') {
          const data = item.data as { name?: string; value?: number; category?: string } | undefined;
          return data ? `<strong>${escapeScientificHtml(data.name)}</strong><br/>Network degree/value: ${formatScientificNumber(Number(data.value))}<br/>Category: ${escapeScientificHtml(data.category)}` : '';
        }
        const data = item?.data as { rawCosine?: number; featureCoverage?: number; sharedFeatures?: number } | undefined;
        return `Adjusted similarity: ${formatScientificNumber(Number(item?.value) * 100)}%<br/>Raw cosine: ${formatScientificNumber(Number(data?.rawCosine) * 100)}%<br/>Shared-feature coverage: ${formatScientificNumber(Number(data?.featureCoverage) * 100)}%<br/>Shared features: ${formatScientificNumber(Number(data?.sharedFeatures))}`;
      } },
      series: [{
        name: 'Similarity network',
        type: 'graph',
        layout: 'force',
        data: nodes.map((node) => ({ id: node.id, name: node.name, value: node.value, category: node.category, symbolSize: Math.max(8, Math.min(24, node.value * 1.6)), itemStyle: { borderColor: theme === 'dark' ? '#0f172a' : '#ffffff', borderWidth: 1 } })),
        links: edges.map((edge) => ({ source: edge.source, target: edge.target, value: edge.value, rawCosine: edge.rawCosine, featureCoverage: edge.featureCoverage, sharedFeatures: edge.sharedFeatures, lineStyle: { width: Math.max(0.4, (edge.value - 0.5) * 3), opacity: Math.max(0.15, Math.min(0.75, edge.value)) } })),
        categories,
        roam: true,
        label: { show: nodes.length <= 80, position: 'right', formatter: '{b}', fontSize: 9, distance: 4 },
        force: { repulsion: nodes.length > 200 ? 55 : 130, edgeLength: [30, 76], gravity: 0.08, layoutAnimation: false },
        emphasis: { focus: 'adjacency', lineStyle: { width: 2.2 } },
        lineStyle: { color: 'source', curveness: 0.08, opacity: 0.45 },
        progressive: 1_000,
      }],
    };
  }, [edges, nodes, theme]);
  return <ScientificEChart option={option} theme={theme} ariaLabel="Overlap-adjusted similarity network" description="Nodes are materials and edges are standardized-feature cosine similarities weighted by shared-feature coverage. Network geometry is descriptive, not proof of identity or causality." exportName="cosine-similarity-network" dataCount={nodes.length + edges.length} empty={nodes.length === 0} />;
});
