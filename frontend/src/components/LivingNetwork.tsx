'use client';

import { useEffect, useRef, useCallback } from 'react';

interface Node {
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
  pulse: number;
  pulseSpeed: number;
}

interface Ripple {
  x: number;
  y: number;
  radius: number;
  maxRadius: number;
  alpha: number;
}

const ACCENT = '#0EECBC';
const NODE_COUNT = 20;
const CONNECTION_DIST = 150;

export default function LivingNetwork({ className = '' }: { className?: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const nodesRef = useRef<Node[]>([]);
  const ripplesRef = useRef<Ripple[]>([]);
  const animRef = useRef<number>(0);

  const initNodes = useCallback((w: number, h: number) => {
    const nodes: Node[] = [];
    for (let i = 0; i < NODE_COUNT; i++) {
      nodes.push({
        x: Math.random() * w,
        y: Math.random() * h,
        vx: (Math.random() - 0.5) * 0.4,
        vy: (Math.random() - 0.5) * 0.4,
        radius: 2 + Math.random() * 2,
        pulse: Math.random() * Math.PI * 2,
        pulseSpeed: 0.02 + Math.random() * 0.02,
      });
    }
    nodesRef.current = nodes;
  }, []);

  const addRipple = useCallback((x: number, y: number) => {
    ripplesRef.current.push({
      x, y,
      radius: 0,
      maxRadius: 60 + Math.random() * 40,
      alpha: 0.5,
    });
    // max 10 ripples
    if (ripplesRef.current.length > 10) {
      ripplesRef.current.shift();
    }
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const resize = () => {
      const { width, height } = container.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      ctx.scale(dpr, dpr);

      if (nodesRef.current.length === 0) {
        initNodes(width, height);
      }
    };
    resize();

    const observer = new ResizeObserver(resize);
    observer.observe(container);

    // Periodic ripples (simulating trade events)
    const rippleInterval = setInterval(() => {
      const w = container.getBoundingClientRect().width;
      const h = container.getBoundingClientRect().height;
      const node = nodesRef.current[Math.floor(Math.random() * nodesRef.current.length)];
      if (node) addRipple(node.x, node.y);
    }, 2000);

    const draw = () => {
      const { width: w, height: h } = container.getBoundingClientRect();
      ctx.clearRect(0, 0, w, h);

      const nodes = nodesRef.current;
      const ripples = ripplesRef.current;

      // Update & draw ripples
      for (let i = ripples.length - 1; i >= 0; i--) {
        const r = ripples[i];
        r.radius += 1.5;
        r.alpha -= 0.008;
        if (r.alpha <= 0 || r.radius > r.maxRadius) {
          ripples.splice(i, 1);
          continue;
        }
        ctx.beginPath();
        ctx.arc(r.x, r.y, r.radius, 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(14, 236, 188, ${r.alpha})`;
        ctx.lineWidth = 1;
        ctx.stroke();
      }

      // Update nodes
      for (const node of nodes) {
        node.x += node.vx;
        node.y += node.vy;
        node.pulse += node.pulseSpeed;

        // Bounce off edges
        if (node.x < 0 || node.x > w) node.vx *= -1;
        if (node.y < 0 || node.y > h) node.vy *= -1;
        node.x = Math.max(0, Math.min(w, node.x));
        node.y = Math.max(0, Math.min(h, node.y));
      }

      // Draw connections
      ctx.lineWidth = 0.5;
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const dx = nodes[i].x - nodes[j].x;
          const dy = nodes[i].y - nodes[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < CONNECTION_DIST) {
            const alpha = 1 - dist / CONNECTION_DIST;
            ctx.beginPath();
            ctx.moveTo(nodes[i].x, nodes[i].y);
            ctx.lineTo(nodes[j].x, nodes[j].y);
            ctx.strokeStyle = `rgba(14, 236, 188, ${alpha * 0.2})`;
            ctx.stroke();
          }
        }
      }

      // Draw nodes
      for (const node of nodes) {
        const glow = 1 + Math.sin(node.pulse) * 0.3;
        const r = node.radius * glow;

        // Glow
        ctx.beginPath();
        ctx.arc(node.x, node.y, r + 4, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(14, 236, 188, ${0.08 * glow})`;
        ctx.fill();

        // Core
        ctx.beginPath();
        ctx.arc(node.x, node.y, r, 0, Math.PI * 2);
        ctx.fillStyle = ACCENT;
        ctx.fill();
      }

      animRef.current = requestAnimationFrame(draw);
    };

    animRef.current = requestAnimationFrame(draw);

    return () => {
      cancelAnimationFrame(animRef.current);
      clearInterval(rippleInterval);
      observer.disconnect();
    };
  }, [initNodes, addRipple]);

  return (
    <div ref={containerRef} className={`absolute inset-0 will-change-transform ${className}`}>
      <canvas ref={canvasRef} className="block w-full h-full" />
    </div>
  );
}
