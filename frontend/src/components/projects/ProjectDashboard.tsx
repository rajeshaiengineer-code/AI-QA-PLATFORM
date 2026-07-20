"use client";

import Link from "next/link";

import { Button } from "@/components/ui/Button";
import {
  EmptyState,
  ErrorState,
  LoadingState,
} from "@/components/ui/Feedback";
import { Input } from "@/components/ui/Input";
import { Pagination } from "@/components/ui/Pagination";
import { ProjectFormModal } from "@/components/projects/ProjectFormModal";
import {
  getErrorMessage,
  useCreateProject,
  useDeleteProject,
  useProjectsQuery,
  useUpdateProject,
} from "@/hooks/useProjects";
import { ROUTES } from "@/lib/constants";
import { formatDateTime } from "@/lib/utils";
import { toProjectPayload } from "@/lib/validators/project";
import { useProjectStore, type ProjectFilters } from "@/store/project.store";

type ProjectPayload = ReturnType<typeof toProjectPayload>;

const DEFAULT_ORG_ID =
  process.env.NEXT_PUBLIC_DEFAULT_ORGANIZATION_ID?.trim() || undefined;

export function ProjectDashboard() {
  const {
    filters,
    setFilters,
    isCreateOpen,
    isEditOpen,
    isDeleteOpen,
    selectedProject,
    openCreate,
    closeCreate,
    openEdit,
    closeEdit,
    openDelete,
    closeDelete,
  } = useProjectStore();

  const listQuery = useProjectsQuery(filters);
  const createMutation = useCreateProject();
  const updateMutation = useUpdateProject();
  const deleteMutation = useDeleteProject();

  const projects = listQuery.data?.items ?? [];
  const total = listQuery.data?.total ?? 0;
  const totalPages = listQuery.data?.total_pages ?? 0;

  const handleCreate = async (values: ProjectPayload) => {
    await createMutation.mutateAsync(values);
    closeCreate();
    createMutation.reset();
  };

  const handleUpdate = async (values: ProjectPayload) => {
    if (!selectedProject) return;
    await updateMutation.mutateAsync({
      id: selectedProject.id,
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
            : `${total} project${total === 1 ? "" : "s"}`}
        </p>
        <Button onClick={openCreate}>Create project</Button>
      </div>

      <div className="grid gap-3 md:grid-cols-[1fr_10rem]">
        <Input
          placeholder="Search by name or key…"
          value={filters.search}
          onChange={(e) => setFilters({ search: e.target.value, page: 1 })}
        />
        <select
          className="h-10 rounded-md border border-border bg-surface px-3 text-sm"
          value={filters.is_active}
          onChange={(e) =>
            setFilters({
              is_active: e.target.value as ProjectFilters["is_active"],
              page: 1,
            })
          }
        >
          <option value="">All statuses</option>
          <option value="true">Active</option>
          <option value="false">Inactive</option>
        </select>
      </div>

      <section className="overflow-hidden rounded-lg border border-border bg-surface">
        {listQuery.isLoading ? (
          <LoadingState message="Loading projects…" />
        ) : listQuery.isError ? (
          <ErrorState
            title="Failed to load projects"
            message={getErrorMessage(listQuery.error)}
            onRetry={() => void listQuery.refetch()}
          />
        ) : projects.length === 0 ? (
          <div className="p-4">
            <EmptyState
              title="No projects yet"
              description="Create a project under an organization to group stories and sprints."
              action={
                <Button onClick={openCreate}>Create your first project</Button>
              }
            />
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead className="border-b border-border bg-surface-muted/60 text-xs uppercase tracking-wide text-muted">
                  <tr>
                    <th className="px-4 py-3 font-medium">Key</th>
                    <th className="px-4 py-3 font-medium">Name</th>
                    <th className="px-4 py-3 font-medium">Status</th>
                    <th className="px-4 py-3 font-medium">Updated</th>
                    <th className="px-4 py-3 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {projects.map((project) => (
                    <tr
                      key={project.id}
                      className="border-b border-border last:border-b-0"
                    >
                      <td className="px-4 py-3 font-mono text-xs">
                        {project.key}
                      </td>
                      <td className="px-4 py-3">
                        <Link
                          href={`${ROUTES.PROJECTS}/${project.id}`}
                          className="font-medium text-accent hover:underline"
                        >
                          {project.name}
                        </Link>
                        {project.description ? (
                          <p className="mt-0.5 line-clamp-1 text-xs text-muted">
                            {project.description}
                          </p>
                        ) : null}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={
                            project.is_active
                              ? "text-xs text-accent"
                              : "text-xs text-muted"
                          }
                        >
                          {project.is_active ? "Active" : "Inactive"}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-xs text-muted">
                        {formatDateTime(project.updated_at)}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => openEdit(project)}
                          >
                            Edit
                          </Button>
                          <Button
                            size="sm"
                            variant="danger"
                            onClick={() => openDelete(project)}
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

      <ProjectFormModal
        open={isCreateOpen}
        mode="create"
        defaultOrganizationId={DEFAULT_ORG_ID}
        loading={createMutation.isPending}
        error={createMutation.error}
        onClose={() => {
          closeCreate();
          createMutation.reset();
        }}
        onSubmit={handleCreate}
      />

      <ProjectFormModal
        open={isEditOpen}
        mode="edit"
        project={selectedProject}
        loading={updateMutation.isPending}
        error={updateMutation.error}
        onClose={() => {
          closeEdit();
          updateMutation.reset();
        }}
        onSubmit={handleUpdate}
      />

      {isDeleteOpen && selectedProject ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-md rounded-lg border border-border bg-surface p-5 shadow-lg">
            <h2 className="text-lg font-semibold">Delete project?</h2>
            <p className="mt-2 text-sm text-muted">
              Soft-delete <strong>{selectedProject.name}</strong> (
              {selectedProject.key}). Stories remain in the database.
            </p>
            {deleteMutation.error ? (
              <p className="mt-2 text-sm text-danger">
                {getErrorMessage(deleteMutation.error)}
              </p>
            ) : null}
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
                  await deleteMutation.mutateAsync(selectedProject.id);
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
