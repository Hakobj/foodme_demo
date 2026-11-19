import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { foodmeApi } from "@/api/foodme";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { StarRatingInput } from "@/components/sections/star-rating";

export const REVIEW_COMMENT_MAX = 1000;

interface RateOrderDialogProps {
  orderNumber: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function RateOrderDialog({ orderNumber, open, onOpenChange }: RateOrderDialogProps) {
  const queryClient = useQueryClient();
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState("");

  const mutation = useMutation({
    mutationFn: () =>
      foodmeApi.reviewOrder(orderNumber, {
        rating,
        comment: comment.trim() ? comment.trim() : undefined,
      }),
    onSuccess: async () => {
      // R12/R17/R19: refresh the order everywhere it is shown, and the chef's storefront rating.
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["my-orders"] }),
        queryClient.invalidateQueries({ queryKey: ["order", orderNumber] }),
        queryClient.invalidateQueries({ queryKey: ["chef"] }),
        queryClient.invalidateQueries({ queryKey: ["chefs"] }),
      ]);
      onOpenChange(false);
    },
  });

  const handleOpenChange = (next: boolean) => {
    if (!next) {
      setRating(0);
      setComment("");
      mutation.reset();
    }
    onOpenChange(next);
  };

  const commentId = `review-comment-${orderNumber}`;

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="p-6">
        <form
          onSubmit={(event) => {
            event.preventDefault();
            if (rating > 0 && !mutation.isPending) mutation.mutate();
          }}
          className="space-y-5"
        >
          <div className="pr-10">
            <DialogTitle className="font-display text-xl font-bold text-zinc-900">
              Rate order {orderNumber}
            </DialogTitle>
            <DialogDescription className="mt-1 text-sm text-zinc-500">
              How was your order? Your rating helps other customers choose.
            </DialogDescription>
          </div>

          <StarRatingInput value={rating} onChange={setRating} disabled={mutation.isPending} />

          <div>
            <label htmlFor={commentId} className="mb-2 block text-sm font-semibold text-zinc-900">
              Comment <span className="font-normal text-zinc-400">(optional)</span>
            </label>
            <textarea
              id={commentId}
              value={comment}
              onChange={(event) => setComment(event.target.value)}
              placeholder="Tell us about your order"
              maxLength={REVIEW_COMMENT_MAX}
              rows={4}
              disabled={mutation.isPending}
              className="w-full resize-none rounded-xl border border-zinc-200 bg-white px-3.5 py-2.5 text-sm text-zinc-900 placeholder:text-zinc-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-900 disabled:opacity-60"
            />
            <p className="mt-1 text-right text-xs tabular-nums text-zinc-400">
              {comment.length}/{REVIEW_COMMENT_MAX}
            </p>
          </div>

          {mutation.isError && (
            <p role="alert" className="rounded-xl border border-red-100 bg-red-50 px-3.5 py-2.5 text-sm text-red-700">
              {mutation.error instanceof Error && mutation.error.message
                ? mutation.error.message
                : "Couldn’t save your rating. Please try again."}
            </p>
          )}

          <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <Button type="button" variant="outline" className="rounded-full" onClick={() => handleOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" className="rounded-full" disabled={rating === 0 || mutation.isPending}>
              {mutation.isPending ? "Submitting…" : "Submit rating"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
