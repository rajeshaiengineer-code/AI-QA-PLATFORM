"use client";

import { Button } from "@/components/ui/Button";
import {
  EmptyState,
  ErrorState,
  LoadingState,
} from "@/components/ui/Feedback";
import { Pagination } from "@/components/ui/Pagination";
import { DeleteStoryDialog } from "@/components/stories/DeleteStoryDialog";
import { StoryDetailsDrawer } from "@/components/stories/StoryDetailsDrawer";
import { StoryFilters } from "@/components/stories/StoryFilters";
import { StoryFormModal } from "@/components/stories/StoryFormModal";
import { StoryTable } from "@/components/stories/StoryTable";
import {
  getErrorMessage,
  useCreateStory,
  useStoriesQuery,
  useUpdateStory,
} from "@/hooks/useStories";
import { toStoryPayload } from "@/lib/validators/story";
import { useStoryStore } from "@/store/story.store";

type StoryPayload = ReturnType<typeof toStoryPayload>;

const DEFAULT_PROJECT_ID =
  process.env.NEXT_PUBLIC_DEFAULT_PROJECT_ID?.trim() || undefined;

export function StoryDashboard() {
  const {
    filters,
    setFilters,
    isCreateOpen,
    isEditOpen,
    selectedStory,
    openCreate,
    closeCreate,
    closeEdit,
  } = useStoryStore();

  const listQuery = useStoriesQuery(filters);
  const createMutation = useCreateStory();
  const updateMutation = useUpdateStory();

  const stories = listQuery.data?.items ?? [];
  const total = listQuery.data?.total ?? 0;
  const totalPages = listQuery.data?.total_pages ?? 0;

  const handleCreate = async (values: StoryPayload) => {
    await createMutation.mutateAsync(values);
    closeCreate();
    createMutation.reset();
  };

  const handleUpdate = async (values: StoryPayload) => {
    if (!selectedStory) return;
    await updateMutation.mutateAsync({
      id: selectedStory.id,
      payload: values,
    });
    closeEdit();
    updateMutation.reset();
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm text-muted">
            {listQuery.isFetching && !listQuery.isLoading
              ? "Refreshing…"
              : `${total} stor${total === 1 ? "y" : "ies"}`}
          </p>
        </div>
        <Button onClick={openCreate}>Create story</Button>
      </div>

      <StoryFilters />

      <section className="overflow-hidden rounded-lg border border-border bg-surface">
        {listQuery.isLoading ? (
          <LoadingState message="Loading stories…" />
        ) : listQuery.isError ? (
          <ErrorState
            title="Failed to load stories"
            message={getErrorMessage(listQuery.error)}
            onRetry={() => void listQuery.refetch()}
          />
        ) : stories.length === 0 ? (
          <div className="p-4">
            <EmptyState
              title="No stories yet"
              description="Create a story linked to an existing project UUID to get started."
              action={
                <Button onClick={openCreate}>Create your first story</Button>
              }
            />
          </div>
        ) : (
          <>
            <StoryTable stories={stories} />
            <Pagination
              page={filters.page}
              pageSize={filters.page_size}
              total={total}
              totalPages={totalPages}
              onPageChange={(page) => setFilters({ page })}
              onPageSizeChange={(page_size) =>
                setFilters({ page_size, page: 1 })
              }
            />
          </>
        )}
      </section>

      <StoryFormModal
        open={isCreateOpen}
        mode="create"
        defaultProjectId={DEFAULT_PROJECT_ID}
        loading={createMutation.isPending}
        error={createMutation.error}
        onClose={() => {
          closeCreate();
          createMutation.reset();
        }}
        onSubmit={handleCreate}
      />

      <StoryFormModal
        open={isEditOpen}
        mode="edit"
        story={selectedStory}
        loading={updateMutation.isPending}
        error={updateMutation.error}
        onClose={() => {
          closeEdit();
          updateMutation.reset();
        }}
        onSubmit={handleUpdate}
      />

      <StoryDetailsDrawer />
      <DeleteStoryDialog />
    </div>
  );
}
