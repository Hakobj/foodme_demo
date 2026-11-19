import { useState } from "react";
import { Star } from "lucide-react";
import { cn } from "@/lib/utils";

const STARS = [1, 2, 3, 4, 5] as const;

function starLabel(value: number) {
  return value === 1 ? "1 star" : `${value} stars`;
}

interface StarRatingInputProps {
  value: number;
  onChange: (value: number) => void;
  disabled?: boolean;
}

/**
 * 1–5 star picker built on native radio buttons, so mouse, touch, keyboard (arrow keys)
 * and screen readers all work without extra wiring (R24).
 */
export function StarRatingInput({ value, onChange, disabled }: StarRatingInputProps) {
  const [hovered, setHovered] = useState(0);
  const shown = hovered || value;

  return (
    <fieldset disabled={disabled} className="min-w-0">
      <legend className="mb-2 text-sm font-semibold text-zinc-900">Your rating</legend>
      <div className="flex items-center gap-1" onMouseLeave={() => setHovered(0)}>
        {STARS.map((star) => (
          <label
            key={star}
            className="group relative cursor-pointer rounded-full p-1 has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-zinc-900 has-[:focus-visible]:ring-offset-2"
            onMouseEnter={() => setHovered(star)}
          >
            <input
              type="radio"
              name="order-rating"
              value={star}
              checked={value === star}
              onChange={() => onChange(star)}
              aria-label={starLabel(star)}
              className="sr-only"
            />
            <Star
              aria-hidden="true"
              size={32}
              strokeWidth={1.5}
              className={cn(
                "transition-colors duration-150",
                star <= shown ? "fill-amber-400 text-amber-400" : "fill-transparent text-zinc-300",
              )}
            />
          </label>
        ))}
      </div>
    </fieldset>
  );
}

interface StarRatingDisplayProps {
  value: number;
  size?: number;
  className?: string;
}

/** Read-only stars, announced as "Rated N out of 5". */
export function StarRatingDisplay({ value, size = 16, className }: StarRatingDisplayProps) {
  return (
    <span role="img" aria-label={`Rated ${value} out of 5`} className={cn("inline-flex items-center gap-0.5", className)}>
      {STARS.map((star) => (
        <Star
          key={star}
          aria-hidden="true"
          size={size}
          strokeWidth={1.5}
          className={star <= value ? "fill-amber-400 text-amber-400" : "fill-transparent text-zinc-300"}
        />
      ))}
    </span>
  );
}
