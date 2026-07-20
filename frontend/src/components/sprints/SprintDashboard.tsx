"use client";

import { useEffect } from "react";
import { useSearchParams } from "next/navigation";

import { Button } from "@/components/ui/Button";
import {
  EmptyState,
  ErrorState,
  LoadingState,
} from "@/components/ui/Feedback";
import { Input } from "@/components/ui/Input";
import { Pagination } from "@/components/ui/Pagination";
import { SprintFormModal } from "@/components/sprints/SprintFormModal";
import {
  getErrorMessage,
  useCreateSprint,
  useDeleteSprint,
  useSprintsQuery,
  useUpdateSprint,
} from "@/hooks/useSprints";
import { formatDateTime } from "@/lib/utils";
import { toSprintPayload } from "@/lib/validators/sprint";
import { useSprintStore, type SprintFilters } from "@/store/sprint.store";

type SprintPayload = ReturnType<typeof toSprintPayload>;

const DEFAULT_PROJECT_ID =
  process.env.NEXT_PUBLIC_DEFAULT_PROJECT_ID?.trim() || undefined;

export function SprintDashboard() {
  const searchParams = useSearchParams();
  const {
    filters,
    setFilters,
    isCreateOpen,
    isEditOpen,
    isDeleteOpen,
    selectedSprint,
    openCreate,
    closeCreate,
    openEdit,
    closeEdit,
    openDelete,
    closeDelete,
  } = useSprintStore();

  useEffect(() => {
    const projectFromUrl = searchParams.get("project_id")?.trim();
    if (projectFromUrl && projectFromUrl !== filters.project_id) {
      setFilters({ project_id: projectFromUrl, page: 1 });
    } else if (!filters.project_id && DEFAULT_PROJECT_ID) {
      setFilters({ project_id: DEFAULT_PROJECT_ID });
    }
  }, [searchParams, filters.project_id, setFilters]);

  const listQuery = useSprintsQuery(filters);
  const createMutation = useCreateSprint();
  const updateMutation = useUpdateSprint();
  const deleteMutation = useDeleteSprint();

  const sprints = listQuery.data?.items ?? [];
  const total = listQuery.data?.total ?? 0;
  const totalPages = listQuery.data?.total_pages ?? 0;

  const handleCreate = async (values: SprintPayload) => {
    await createMutation.mutateAsync(values);
    closeCreate();
    createMutation.reset();
  };

  const handleUpdate = async (values: SprintPayload) => {
    if (!selectedSprint) return;
    await updateMutation.mutateAsync({
      id: selectedSprint.id,
      payload: values,
    });
    closeEdit();
    updateMutation.reset();
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-muted">
          {listQuery.isFetching && !listQuery.isLoading
            ? "Refreshing…"
            : `${total} sprint${total === 1 ? "" : "s"}`}
        </p>
        <Button onClick={openCreate}>Create sprint</Button>
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        <Input
          label="Project ID"
          value={filters.project_id}
          onChange={(e) =>
            setFilters({ project_id: e.target.value, page: 1 })
          }
        />
        <Input
          label="Search"
          placeholder="Search by name or goal…"
          value={filters.search}
          onChange={(e) => setFilters({ search: e.target.value, page: 1 })}
        />
        <label className="flex w-full flex-col gap-1.5 text-sm">
          <span className="font-medium text-foreground">Status</span>
          <select
            className="h-10 rounded-md border border-border bg-surface px-3 text-sm"
            value={filters.is_active}
            onChange={(e) =>
              setFilters({
                is_active: e.target.value as SprintFilters["is_active"],
                page: 1,
              })
            }
          >
            <option value="">All</option>
            <option value="true">Active</option>
            <option value="false">Inactive</option>
          </select>
        </label>
      </div>

      <section className="overflow-hidden rounded-lg border border-border bg-surface">
        {listQuery.isLoading ? (
          <LoadingState message="Loading sprints…" />
        ) : listQuery.isError ? (
          <ErrorState
            title="Failed to load sprints"
            message={getErrorMessage(listQuery.error)}
            onRetry={() => void listQuery.refetch()}
          />
        ) : sprints.length === 0 ? (
          <div className="p-4">
            <EmptyState
              title="No sprints yet"
              description="Create a sprint under a project to plan stories."
              action={
                <Button onClick={openCreate}>Create your first sprint</Button>
              }
            />
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead className="border-b border-border bg-surface-muted/60 text-xs uppercase tracking-wide text-muted">
                  <tr>
                    <th className="px-4 py-3 font-medium">Name</th>
                    <th className="px-4 py-3 font-medium">Dates</th>
                    <th className="px-4 py-3 font-medium">Status</th>
                    <th className="px-4 py-3 font-medium">Updated</th>
                    <th className="px-4 py-3 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {sprints.map((sprint) => (
                    <tr
                      key={sprint.id}
                      className="border-b border-border last:border-b-0"
                    >
                      <td className="px-4 py-3">
                        <p className="font-medium">{sprint.name}</p>
                        {sprint.goal ? (
                          <p className="mt-0.5 line-clamp-1 text-xs text-muted">
                            {sprint.goal}
                          </p>
                        ) : null}
                      </td>
                      <td className="px-4 py-3 text-xs text-muted">
                        {sprint.start_date || "—"} → {sprint.end_date || "—"}
                      </td>
                      <td className="px-4 py-3 text-xs">
                        {sprint.is_active ? "Active" : "Inactive"}
                      </td>
                      <td className="px-4 py-3 text-xs text-muted">
                        {formatDateTime(sprint.updated_at)}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => openEdit(sprint)}
                          >
                            Edit
                          </Button>
                          <Button
                            size="sm"
                            variant="danger"
                            onClick={() => openDelete(sprint)}
                          >
                            Delete
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
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

      <SprintFormModal
        open={isCreateOpen}
        mode="create"
        defaultProjectId={filters.project_id || DEFAULT_PROJECT_ID}
        loading={createMutation.isPending}
        error={createMutation.error}
        onClose={() => {
          closeCreate();
          createMutation.reset();
        }}
        onSubmit={handleCreate}
      />

      <SprintFormModal
        open={isEditOpen}
        mode="edit"
        sprint={selectedSprint}
        loading={updateMutation.isPending}
        error={updateMutation.error}
        onClose={() => {
          closeEdit();
          updateMutation.reset();
        }}
        onSubmit={handleUpdate}
      />

      {isDeleteOpen && selectedSprint ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-md rounded-lg border border-border bg-surface p-5 shadow-lg">
            <h2 className="text-lg font-semibold">Delete sprint?</h2>
            <p className="mt-2 text-sm text-muted">
              Soft-delete <strong>{selectedSprint.name}</strong>. Linked stories
              keep their sprint_id until reassigned.
            </p>
            <div className="mt-4 flex justify-end gap-2">
              <Button
                variant="secondary"
                onClick={() => {
                  closeDelete();
                  deleteMutation.reset();
                }}
              >
                Cancel
              </Button>
              <Button
                variant="danger"
                loading={deleteMutation.isPending}
                onClick={async () => {
                  await deleteMutation.mutateAsync(selectedSprint.id);
                  closeDelete();
                  deleteMutation.reset();
                }}
              >
                Delete
              </Button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
