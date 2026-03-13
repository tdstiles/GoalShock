import { useEffect, useRef } from 'react';

// OPTIMIZATION: Render at lower resolution to save CPU cycles
// 0.5 means 1/2 width and 1/2 height -> 1/4 total pixels to process
const RESOLUTION_SCALE = 0.5;

// Water configuration constants
const WATER_DAMPING = 0.95;
const WATER_DROP_RADIUS = 5;
const WATER_DROP_STRENGTH = 200;
const WATER_AMBIENT_INTERVAL_MS = 3000;
const WATER_BASE_GREEN = 14;
const WATER_BASE_BLUE = 27;

// Internal Physics and Display Constants
const WATER_DISTORTION_FACTOR = 1.5;
const WATER_COLOR_MAX_GREEN = 70;
const WATER_COLOR_DEPTH_GREEN_MULTIPLIER = 0.6;
const WATER_COLOR_MAX_BLUE = 80;
const WATER_COLOR_DEPTH_BLUE_MULTIPLIER = 0.7;

// Mouse Interaction Constants
const MOUSE_VELOCITY_MAX = 1.5;
const MOUSE_VELOCITY_DIVISOR = 100;

// Ambient Ripple Constants
const AMBIENT_RIPPLE_SIZE_MULTIPLIER = 0.6;
const AMBIENT_RIPPLE_STRENGTH_MULTIPLIER = 0.25;

export default function SubtleRippleBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Set canvas size (scaled down for performance)
    const resize = () => {
      canvas.width = window.innerWidth * RESOLUTION_SCALE;
      canvas.height = window.innerHeight * RESOLUTION_SCALE;
    };
    resize();
    window.addEventListener('resize', resize);

    // Water ripple simulation
    const width = canvas.width;
    const height = canvas.height;

    let current = new Float32Array(width * height);
    let previous = new Float32Array(width * height);

    // OPTIMIZED WATER PARAMETERS - better performance
    const damping = WATER_DAMPING;          // Faster fade for better performance
    const dropRadius = WATER_DROP_RADIUS;           // Smaller ripples for better performance
    const dropStrength = WATER_DROP_STRENGTH;       // Reduced strength for smoother animation

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
          const offsetX = Math.round(x + dx * WATER_DISTORTION_FACTOR);
          const offsetY = Math.round(y + dy * WATER_DISTORTION_FACTOR);

          if (offsetX >= 0 && offsetX < width && offsetY >= 0 && offsetY < height) {
            const pixelIndex = (y * width + x) * 4;

            // Enhanced green-teal water color with gradient depth
            const depth = Math.abs(previous[index]);
            const green = WATER_BASE_GREEN + Math.min(WATER_COLOR_MAX_GREEN, depth * WATER_COLOR_DEPTH_GREEN_MULTIPLIER);
            const blue = WATER_BASE_BLUE + Math.min(WATER_COLOR_MAX_BLUE, depth * WATER_COLOR_DEPTH_BLUE_MULTIPLIER);

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
      // Scale mouse coordinates to match the scaled canvas
      const x = Math.floor(e.clientX * RESOLUTION_SCALE);
      const y = Math.floor(e.clientY * RESOLUTION_SCALE);

      // Calculate movement distance
      const dx = Math.abs(x - lastX);
      const dy = Math.abs(y - lastY);

      // Create smooth ripples on movement with dynamic strength
      if (dx + dy > 2) {
        const velocity = Math.min(MOUSE_VELOCITY_MAX, (dx + dy) / MOUSE_VELOCITY_DIVISOR);
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
      const size = dropRadius * AMBIENT_RIPPLE_SIZE_MULTIPLIER;
      const strength = dropStrength * AMBIENT_RIPPLE_STRENGTH_MULTIPLIER;
      drop(x, y, size, strength);
    };

    const ambientInterval = setInterval(createAmbientRipple, WATER_AMBIENT_INTERVAL_MS);

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
