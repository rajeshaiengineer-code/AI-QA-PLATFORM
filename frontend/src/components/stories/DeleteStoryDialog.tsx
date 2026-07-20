"use client";

import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { getErrorMessage, useDeleteStory } from "@/hooks/useStories";
import { useStoryStore } from "@/store/story.store";

export function DeleteStoryDialog() {
  const { isDeleteOpen, selectedStory, closeDelete, closeDrawer } =
    useStoryStore();
  const deleteMutation = useDeleteStory();

  if (!selectedStory) return null;

  return (
    <Modal
      open={isDeleteOpen}
      title="Delete story"
      description={`Soft-delete “${selectedStory.title}”? It will no longer appear in lists.`}
      onClose={() => {
        closeDelete();
        deleteMutation.reset();
      }}
      footer={
        <div className="flex flex-col gap-3">
          {deleteMutation.isError ? (
            <p className="text-sm text-danger">
              {getErrorMessage(deleteMutation.error)}
            </p>
          ) : null}
          <div className="flex justify-end gap-2">
            <Button
              variant="secondary"
              onClick={() => {
                closeDelete();
                deleteMutation.reset();
              }}
              disabled={deleteMutation.isPending}
            >
              Cancel
            </Button>
            <Button
              variant="danger"
              loading={deleteMutation.isPending}
              onClick={async () => {
                await deleteMutation.mutateAsync(selectedStory.id);
                closeDelete();
                closeDrawer();
              }}
            >
              Delete
            </Button>
          </div>
        </div>
      }
    />
  );
}
