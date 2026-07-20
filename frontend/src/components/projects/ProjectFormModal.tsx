"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect } from "react";
import { useForm } from "react-hook-form";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Textarea } from "@/components/ui/Textarea";
import { getErrorMessage } from "@/hooks/useProjects";
import {
  projectFormSchema,
  type ProjectFormValues,
  toProjectPayload,
} from "@/lib/validators/project";
import type { Project } from "@/types/project";

type ProjectPayload = ReturnType<typeof toProjectPayload>;

interface ProjectFormModalProps {
  open: boolean;
  mode: "create" | "edit";
  project?: Project | null;
  defaultOrganizationId?: string;
  loading?: boolean;
  error?: unknown;
  onClose: () => void;
  onSubmit: (values: ProjectPayload) => Promise<void>;
}

export function ProjectFormModal({
  open,
  mode,
  project,
  defaultOrganizationId,
  loading,
  error,
  onClose,
  onSubmit,
}: ProjectFormModalProps) {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<ProjectFormValues>({
    resolver: zodResolver(projectFormSchema),
    defaultValues: {
      organization_id: defaultOrganizationId || "",
      name: "",
      key: "",
      description: "",
      is_active: true,
    },
  });

  useEffect(() => {
    if (!open) return;
    if (mode === "edit" && project) {
      reset({
        organization_id: project.organization_id,
        name: project.name,
        key: project.key,
        description: project.description || "",
        is_active: project.is_active,
      });
    } else {
      reset({
        organization_id: defaultOrganizationId || "",
        name: "",
        key: "",
        description: "",
        is_active: true,
      });
    }
  }, [open, mode, project, defaultOrganizationId, reset]);

  return (
    <Modal
      open={open}
      title={mode === "create" ? "Create project" : "Edit project"}
      onClose={onClose}
    >
      <form
        className="space-y-4"
        onSubmit={handleSubmit(async (values) => {
          await onSubmit(toProjectPayload(values));
        })}
      >
        <Input
          label="Organization ID"
          error={errors.organization_id?.message}
          disabled={mode === "edit"}
          {...register("organization_id")}
        />
        <Input
          label="Name"
          error={errors.name?.message}
          {...register("name")}
        />
        <Input
          label="Key"
          error={errors.key?.message}
          placeholder="PAY"
          {...register("key")}
        />
        <Textarea
          label="Description"
          error={errors.description?.message}
          rows={3}
          {...register("description")}
        />
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" {...register("is_active")} />
          <span>Active</span>
        </label>

        {error ? (
          <p className="text-sm text-danger">{getErrorMessage(error)}</p>
        ) : null}

        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={loading}>
            {mode === "create" ? "Create" : "Save"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
