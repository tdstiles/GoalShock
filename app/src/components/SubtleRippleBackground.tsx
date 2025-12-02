import { useEffect, useRef } from 'react';

export default function SubtleRippleBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Set canvas size
    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    resize();
    window.addEventListener('resize', resize);

    // Water ripple simulation
    const width = canvas.width;
    const height = canvas.height;

    let current = new Float32Array(width * height);
    let previous = new Float32Array(width * height);

    // OPTIMIZED WATER PARAMETERS - better performance
    const damping = 0.95;          // Faster fade for better performance
    const dropRadius = 5;           // Smaller ripples for better performance
    const dropStrength = 200;       // Reduced strength for smoother animation

    // Create smooth ripples
    const drop = (x: number, y: number, radius: number, strength: number) => {
      for (let i = -radius; i < radius; i++) {
        for (let j = -radius; j < radius; j++) {
          const dist = Math.sqrt(i * i + j * j);
          if (dist < radius) {
            const px = Math.floor(x + i);
            const py = Math.floor(y + j);
            if (px >= 0 && px < width && py >= 0 && py < height) {
              const index = py * width + px;
              // Smooth Gaussian-like distribution
              current[index] += strength * (1 - dist / radius);
            }
          }
        }
      }
    };

    // Water physics update
    const update = () => {
      for (let y = 1; y < height - 1; y++) {
        for (let x = 1; x < width - 1; x++) {
          const index = y * width + x;

          // Smooth wave propagation
          current[index] = (
            (previous[index - 1] +
             previous[index + 1] +
             previous[index - width] +
             previous[index + width]) / 2 -
            current[index]
          ) * damping;
        }
      }

      // Swap buffers
      [current, previous] = [previous, current];
    };

    // Render water distortion
    const render = () => {
      const imageData = ctx.createImageData(width, height);
      const data = imageData.data;

      for (let y = 1; y < height - 1; y++) {
        for (let x = 1; x < width - 1; x++) {
          const index = y * width + x;

          // Calculate distortion from water height differences
          const dx = previous[index - 1] - previous[index + 1];
          const dy = previous[index - width] - previous[index + width];

          // Apply SMOOTH distortion offset for water-like effect
          const offsetX = Math.round(x + dx * 1.5);
          const offsetY = Math.round(y + dy * 1.5);

          if (offsetX >= 0 && offsetX < width && offsetY >= 0 && offsetY < height) {
            const pixelIndex = (y * width + x) * 4;

            // Enhanced green-teal water color with gradient depth
            const depth = Math.abs(previous[index]);
            const green = 14 + Math.min(70, depth * 0.6);
            const blue = 27 + Math.min(80, depth * 0.7);

            data[pixelIndex] = 10;         // R
            data[pixelIndex + 1] = green;  // G - varies with depth
            data[pixelIndex + 2] = blue;   // B - varies with depth
            data[pixelIndex + 3] = 255;    // A
          }
        }
      }

      ctx.putImageData(imageData, 0, 0);
    };

    // Mouse interaction - smooth water ripples
    let lastX = 0;
    let lastY = 0;

    const handleMouseMove = (e: MouseEvent) => {
      const x = Math.floor(e.clientX);
      const y = Math.floor(e.clientY);

      // Calculate movement distance
      const dx = Math.abs(x - lastX);
      const dy = Math.abs(y - lastY);

      // Create smooth ripples on movement with dynamic strength
      if (dx + dy > 2) {
        const velocity = Math.min(1.5, (dx + dy) / 100);
        drop(x, y, dropRadius, dropStrength * velocity);
      }

      lastX = x;
      lastY = y;
    };

    canvas.addEventListener('mousemove', handleMouseMove, { passive: true });

    // Random ambient ripples - less frequent for better performance
    const createAmbientRipple = () => {
      const x = Math.random() * width;
      const y = Math.random() * height;
      const size = dropRadius * 0.6;
      const strength = dropStrength * 0.25;
      drop(x, y, size, strength);
    };

    const ambientInterval = setInterval(createAmbientRipple, 3000);

    // Animation loop
    let animationId: number;
    const animate = () => {
      update();
      render();
      animationId = requestAnimationFrame(animate);
    };
    animate();

    return () => {
      window.removeEventListener('resize', resize);
      canvas.removeEventListener('mousemove', handleMouseMove);
      clearInterval(ambientInterval);
      cancelAnimationFrame(animationId);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        zIndex: -1,
        opacity: 0.3,  // Reduced opacity for better performance
        pointerEvents: 'none'
      }}
    />
  );
}
