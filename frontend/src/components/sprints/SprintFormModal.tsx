"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect } from "react";
import { useForm } from "react-hook-form";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Textarea } from "@/components/ui/Textarea";
import { getErrorMessage } from "@/hooks/useSprints";
import {
  sprintFormSchema,
  type SprintFormValues,
  toSprintPayload,
} from "@/lib/validators/sprint";
import type { Sprint } from "@/types/sprint";

type SprintPayload = ReturnType<typeof toSprintPayload>;

interface SprintFormModalProps {
  open: boolean;
  mode: "create" | "edit";
  sprint?: Sprint | null;
  defaultProjectId?: string;
  loading?: boolean;
  error?: unknown;
  onClose: () => void;
  onSubmit: (values: SprintPayload) => Promise<void>;
}

export function SprintFormModal({
  open,
  mode,
  sprint,
  defaultProjectId,
  loading,
  error,
  onClose,
  onSubmit,
}: SprintFormModalProps) {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<SprintFormValues>({
    resolver: zodResolver(sprintFormSchema),
    defaultValues: {
      project_id: defaultProjectId || "",
      name: "",
      goal: "",
      start_date: "",
      end_date: "",
      is_active: true,
    },
  });

  useEffect(() => {
    if (!open) return;
    if (mode === "edit" && sprint) {
      reset({
        project_id: sprint.project_id,
        name: sprint.name,
        goal: sprint.goal || "",
        start_date: sprint.start_date || "",
        end_date: sprint.end_date || "",
        is_active: sprint.is_active,
      });
    } else {
      reset({
        project_id: defaultProjectId || "",
        name: "",
        goal: "",
        start_date: "",
        end_date: "",
        is_active: true,
      });
    }
  }, [open, mode, sprint, defaultProjectId, reset]);

  return (
    <Modal
      open={open}
      title={mode === "create" ? "Create sprint" : "Edit sprint"}
      onClose={onClose}
    >
      <form
        className="space-y-4"
        onSubmit={handleSubmit(async (values) => {
          await onSubmit(toSprintPayload(values));
        })}
      >
        <Input
          label="Project ID"
          error={errors.project_id?.message}
          disabled={mode === "edit"}
          {...register("project_id")}
        />
        <Input
          label="Name"
          error={errors.name?.message}
          {...register("name")}
        />
        <Textarea
          label="Goal"
          error={errors.goal?.message}
          rows={3}
          {...register("goal")}
        />
        <div className="grid gap-3 sm:grid-cols-2">
          <Input
            label="Start date"
            type="date"
            error={errors.start_date?.message}
            {...register("start_date")}
          />
          <Input
            label="End date"
            type="date"
            error={errors.end_date?.message}
            {...register("end_date")}
          />
        </div>
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
