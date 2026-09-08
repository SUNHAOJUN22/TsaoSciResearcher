import React, { useEffect, useRef, useState, useMemo, useCallback } from 'react';
import { Product } from '@/types/index';
import { KMeansBackendCalibrationPanel } from './KMeansBackendCalibrationPanel';

interface Point {
    x: number;
    y: number;
    data: Product;
}

interface QuadTreeNode {
    boundary: { x: number, y: number, w: number, h: number };
    capacity: number;
    points: Point[];
    divided: boolean;
    northWest?: QuadTreeNode;
    northEast?: QuadTreeNode;
    southWest?: QuadTreeNode;
    southEast?: QuadTreeNode;
}

class QuadTree {
    root: QuadTreeNode;

    constructor(boundary: { x: number, y: number, w: number, h: number }, capacity: number = 4) {
        this.root = { boundary, capacity, points: [], divided: false };
    }

    insert(p: Point, node: QuadTreeNode = this.root): boolean {
        if (!this.contains(node.boundary, p)) return false;

        if (node.points.length < node.capacity && !node.divided) {
            node.points.push(p);
            return true;
        }

        if (!node.divided) {
            this.subdivide(node);
        }

        return (
            this.insert(p, node.northWest!) ||
            this.insert(p, node.northEast!) ||
            this.insert(p, node.southWest!) ||
            this.insert(p, node.southEast!)
        );
    }

    subdivide(node: QuadTreeNode) {
        const x = node.boundary.x;
        const y = node.boundary.y;
        const w = node.boundary.w / 2;
        const h = node.boundary.h / 2;

        node.northWest = { boundary: { x, y, w, h }, capacity: node.capacity, points: [], divided: false };
        node.northEast = { boundary: { x: x + w, y, w, h }, capacity: node.capacity, points: [], divided: false };
        node.southWest = { boundary: { x, y: y + h, w, h }, capacity: node.capacity, points: [], divided: false };
        node.southEast = { boundary: { x: x + w, y: y + h, w, h }, capacity: node.capacity, points: [], divided: false };
        node.divided = true;
    }

    contains(b: { x: number, y: number, w: number, h: number }, p: Point) {
        return (p.x >= b.x && p.x <= b.x + b.w && p.y >= b.y && p.y <= b.y + b.h);
    }

    query(range: { x: number, y: number, w: number, h: number }, node: QuadTreeNode = this.root, found: Point[] = []) {
        if (!this.intersects(node.boundary, range)) return found;

        for (const p of node.points) {
            if (this.contains(range, p)) found.push(p);
        }

        if (node.divided) {
           this.query(range, node.northWest!, found);
           this.query(range, node.northEast!, found);
           this.query(range, node.southWest!, found);
           this.query(range, node.southEast!, found);
        }

        return found;
    }

    intersects(b1: { x: number, y: number, w: number, h: number }, b2: { x: number, y: number, w: number, h: number }) {
        return !(b2.x > b1.x + b1.w || 
                 b2.x + b2.w < b1.x || 
                 b2.y > b1.y + b1.h ||
                 b2.y + b2.h < b1.y);
    }
}

interface CanvasScatterGraphProps {
  data: Product[];
  xKey: string;
  yKey: string;
  xLabel?: string;
  yLabel?: string;
  xValues: number[];
  yValues: number[];
  clusters?: Record<string, number>;
  paretoFrontIds?: Set<string>;
  enableConvexHull?: boolean;
}

import { grahamScan, Point2D } from '@/lib/math/convexHull';

export const CanvasScatterGraph: React.FC<CanvasScatterGraphProps> = ({ 
    data, xKey, yKey, xLabel = xKey, yLabel = yKey, xValues, yValues, clusters, paretoFrontIds, enableConvexHull
}) => {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);
    const qTreeRef = useRef<QuadTree | null>(null);
    const [hoveredPoint, setHoveredPoint] = useState<{ point: Point, sx: number, sy: number } | null>(null);
    
    // Coordinates mapping
    const { minX, maxX, minY, maxY } = useMemo(() => {
        let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
        for (let i = 0; i < data.length; i++) {
            if (xValues[i] < minX) minX = xValues[i];
            if (xValues[i] > maxX) maxX = xValues[i];
            if (yValues[i] < minY) minY = yValues[i];
            if (yValues[i] > maxY) maxY = yValues[i];
        }
        if (minX === Infinity) return { minX: 0, maxX: 1, minY: 0, maxY: 1 };
        return { minX, maxX, minY, maxY };
    }, [data, xValues, yValues]);

    useEffect(() => {
        if (!canvasRef.current || !containerRef.current) return;
        
        const canvas = canvasRef.current;
        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        const rect = containerRef.current.getBoundingClientRect();
        const width = rect.width;
        const height = rect.height;
        
        const dpr = window.devicePixelRatio || 1;
        canvas.width = width * dpr;
        canvas.height = height * dpr;
        ctx.scale(dpr, dpr);
        canvas.style.width = `${width}px`;
        canvas.style.height = `${height}px`;

        const padding = 40;
        const innerW = width - padding * 2;
        const innerH = height - padding * 2;

        const mapX = (val: number) => padding + ((val - minX) / (maxX - minX || 1)) * innerW;
        const mapY = (val: number) => height - padding - ((val - minY) / (maxY - minY || 1)) * innerH;

        ctx.clearRect(0, 0, width, height);

        // Draw axes
        ctx.strokeStyle = '#e2e8f0';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(padding, padding);
        ctx.lineTo(padding, height - padding);
        ctx.lineTo(width - padding, height - padding);
        ctx.stroke();

        ctx.fillStyle = '#94a3b8';
        ctx.font = '12px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(xLabel, width / 2, height - 10);
        
        ctx.save();
        ctx.translate(15, height / 2);
        ctx.rotate(-Math.PI / 2);
        ctx.fillText(yLabel, 0, 0);
        ctx.restore();

        // Build QuadTree
        const qt = new QuadTree({ x: 0, y: 0, w: width, h: height }, 10);

        // Draw points
        const colors = [
          'rgba(99, 102, 241, 0.6)', // indigo
          'rgba(239, 68, 68, 0.6)',  // red
          'rgba(34, 197, 94, 0.6)',  // green
          'rgba(234, 179, 8, 0.6)',  // yellow
          'rgba(168, 85, 247, 0.6)', // purple
          'rgba(236, 72, 153, 0.6)', // pink
          'rgba(14, 165, 233, 0.6)', // light blue
          'rgba(249, 115, 22, 0.6)', // orange
          'rgba(16, 185, 129, 0.6)', // emerald
          'rgba(100, 116, 139, 0.6)',// slate
        ];
        
        ctx.fillStyle = 'rgba(99, 102, 241, 0.6)';
        
        // --- 1. Convex Hull per Manufacturer ---
        if (enableConvexHull) {
            const pointsByManufacturer: Record<string, Point2D[]> = {};
            for (let i = 0; i < data.length; i++) {
                const manufacturer = data[i].manufacturer || 'Unknown';
                if (!pointsByManufacturer[manufacturer]) pointsByManufacturer[manufacturer] = [];
                pointsByManufacturer[manufacturer].push({
                   x: xValues[i],
                   y: yValues[i],
                   id: data[i].id
                });
            }
            
            const manufacturers = Object.keys(pointsByManufacturer);
            manufacturers.forEach((mfs, idx) => {
                const pts = pointsByManufacturer[mfs];
                if (pts.length >= 3) {
                    const hullPts = grahamScan(pts);
                    if (hullPts.length > 0) {
                        ctx.beginPath();
                        const first = hullPts[0];
                        ctx.moveTo(mapX(first.x), mapY(first.y));
                        for (let j = 1; j < hullPts.length; j++) {
                            ctx.lineTo(mapX(hullPts[j].x), mapY(hullPts[j].y));
                        }
                        ctx.closePath();
                        
                        const colorIdx = idx % colors.length;
                        ctx.fillStyle = colors[colorIdx].replace('0.6', '0.15'); // very transparent
                        ctx.fill();
                        ctx.strokeStyle = colors[colorIdx].replace('0.6', '0.8');
                        ctx.lineWidth = 1.5;
                        ctx.stroke();
                    }
                }
            });
        }
        
        // --- 2. Scatter Points ---
        for (let i = 0; i < data.length; i++) {
            const x = mapX(xValues[i]);
            const y = mapY(yValues[i]);
            
            if (clusters && clusters[data[i].id] !== undefined) {
                const cIdx = clusters[data[i].id] % colors.length;
                ctx.fillStyle = colors[cIdx];
            } else {
                ctx.fillStyle = 'rgba(99, 102, 241, 0.6)';
            }
            
            const isPareto = paretoFrontIds && paretoFrontIds.has(data[i].id);
            if (isPareto) {
               ctx.fillStyle = '#f59e0b'; // Amber-500
               ctx.beginPath();
               ctx.arc(x, y, 5, 0, Math.PI * 2);
               ctx.fill();
               ctx.strokeStyle = '#fff';
               ctx.lineWidth = 1;
               ctx.stroke();
            } else {
               ctx.beginPath();
               ctx.arc(x, y, 3, 0, Math.PI * 2);
               ctx.fill();
            }

            qt.insert({ x, y, data: data[i] });
        }
        
        // --- 3. Pareto Frontier Line ---
        if (paretoFrontIds && paretoFrontIds.size > 0) {
            const currentParetoPts: {x: number, y: number}[] = [];
            for (let i = 0; i < data.length; i++) {
                if (paretoFrontIds.has(data[i].id)) {
                    currentParetoPts.push({ x: mapX(xValues[i]), y: mapY(yValues[i]) });
                }
            }
            
            // Sort by X to draw a smooth bounding line
            currentParetoPts.sort((a, b) => a.x - b.x);
            
            if (currentParetoPts.length > 1) {
                ctx.beginPath();
                ctx.moveTo(currentParetoPts[0].x, currentParetoPts[0].y);
                for (let i = 1; i < currentParetoPts.length; i++) {
                    ctx.lineTo(currentParetoPts[i].x, currentParetoPts[i].y);
                }
                ctx.strokeStyle = 'rgba(245, 158, 11, 0.8)'; // thick outline
                ctx.lineWidth = 2.5;
                // Add dash for skyline feel
                ctx.setLineDash([5, 5]);
                ctx.stroke();
                ctx.setLineDash([]);
            }
        }
        
        qTreeRef.current = qt;
    }, [data, minX, maxX, minY, maxY, xLabel, yLabel, xValues, yValues, clusters, paretoFrontIds, enableConvexHull]);

    const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
        if (!qTreeRef.current || !canvasRef.current) return;
        const rect = canvasRef.current.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;

        const range = { x: mouseX - 5, y: mouseY - 5, w: 10, h: 10 };
        const found = qTreeRef.current.query(range);

        if (found.length > 0) {
            // Find closest
            let closest = found[0];
            let minDist = Infinity;
            for (const p of found) {
                const dist = (p.x - mouseX) ** 2 + (p.y - mouseY) ** 2;
                if (dist < minDist) {
                    minDist = dist;
                    closest = p;
                }
            }
            setHoveredPoint({ point: closest, sx: e.clientX, sy: e.clientY });
        } else {
            setHoveredPoint(null);
        }
    }, []);

    return (
        <div ref={containerRef} className="w-full h-full relative" onMouseLeave={() => setHoveredPoint(null)}>
            <KMeansBackendCalibrationPanel />
            <canvas 
                ref={canvasRef} 
                onMouseMove={handleMouseMove}
                className="cursor-crosshair absolute inset-0"
            />
            {hoveredPoint && (
                <div 
                    className="fixed z-50 bg-slate-900 text-white text-xs p-2 rounded shadow-xl pointer-events-none transform -translate-x-1/2 -translate-y-[calc(100%+10px)] whitespace-nowrap"
                    style={{ left: hoveredPoint.sx, top: hoveredPoint.sy }}
                >
                    <div className="font-bold text-indigo-400 mb-1">{hoveredPoint.point.data.gradeName}</div>
                    <div>{xLabel}: {hoveredPoint.point.data.properties?.[xKey]?.value || '-'}</div>
                    <div>{yLabel}: {hoveredPoint.point.data.properties?.[yKey]?.value || '-'}</div>
                </div>
            )}
        </div>
    );
};
