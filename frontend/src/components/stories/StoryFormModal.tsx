"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect } from "react";
import { Controller, useForm } from "react-hook-form";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Select } from "@/components/ui/Select";
import { Textarea } from "@/components/ui/Textarea";
import { getErrorMessage } from "@/hooks/useStories";
import {
  storyFormSchema,
  toStoryPayload,
  type StoryFormValues,
} from "@/lib/validators/story";
import {
  PRIORITY_OPTIONS,
  STORY_STATUS_OPTIONS,
  STORY_TYPE_OPTIONS,
  type Story,
} from "@/types/story";

interface StoryFormModalProps {
  open: boolean;
  mode: "create" | "edit";
  story?: Story | null;
  defaultProjectId?: string;
  loading?: boolean;
  error?: unknown;
  onClose: () => void;
  onSubmit: (values: ReturnType<typeof toStoryPayload>) => Promise<void> | void;
}

const emptyDefaults: StoryFormValues = {
  project_id: "",
  title: "",
  description: "",
  status: "draft",
  story_type: "feature",
  priority: "medium",
  story_points: null,
  external_id: null,
  rank: null,
  sprint_id: null,
};

export function StoryFormModal({
  open,
  mode,
  story,
  defaultProjectId,
  loading,
  error,
  onClose,
  onSubmit,
}: StoryFormModalProps) {
  const {
    register,
    control,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<StoryFormValues>({
    resolver: zodResolver(storyFormSchema),
    defaultValues: emptyDefaults,
  });

  useEffect(() => {
    if (!open) return;
    if (mode === "edit" && story) {
      reset({
        project_id: story.project_id,
        title: story.title,
        description: story.description ?? "",
        status: story.status,
        story_type: story.story_type,
        priority: story.priority,
        story_points: story.story_points,
        external_id: story.external_id,
        rank: story.rank,
        sprint_id: story.sprint_id,
      });
    } else {
      reset({
        ...emptyDefaults,
        project_id:
          defaultProjectId ||
          process.env.NEXT_PUBLIC_DEFAULT_PROJECT_ID ||
          "",
      });
    }
  }, [open, mode, story, defaultProjectId, reset]);

  return (
    <Modal
      open={open}
      title={mode === "create" ? "Create story" : "Edit story"}
      description={
        mode === "create"
          ? "Requires an existing project UUID until Project Management ships."
          : "Update story fields. Only changed values are sent."
      }
      onClose={onClose}
      footer={
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose} disabled={loading}>
            Cancel
          </Button>
          <Button
            loading={loading}
            onClick={handleSubmit(async (values) => {
              await onSubmit(toStoryPayload(values));
            })}
          >
            {mode === "create" ? "Create" : "Save changes"}
          </Button>
        </div>
      }
    >
      <form className="grid gap-3" onSubmit={(e) => e.preventDefault()}>
        <Input
          label="Project ID"
          error={errors.project_id?.message}
          {...register("project_id")}
        />
        <Input
          label="Title"
          error={errors.title?.message}
          {...register("title")}
        />
        <Textarea
          label="Description"
          error={errors.description?.message}
          {...register("description")}
        />
        <div className="grid gap-3 sm:grid-cols-3">
          <Select
            label="Status"
            options={STORY_STATUS_OPTIONS}
            error={errors.status?.message}
            {...register("status")}
          />
          <Select
            label="Type"
            options={STORY_TYPE_OPTIONS}
            error={errors.story_type?.message}
            {...register("story_type")}
          />
          <Select
            label="Priority"
            options={PRIORITY_OPTIONS}
            error={errors.priority?.message}
            {...register("priority")}
          />
        </div>
        <div className="grid gap-3 sm:grid-cols-3">
          <Controller
            name="story_points"
            control={control}
            render={({ field }) => (
              <Input
                label="Story points"
                type="number"
                min={0}
                max={100}
                value={field.value ?? ""}
                onChange={(e) =>
                  field.onChange(
                    e.target.value === "" ? null : Number(e.target.value)
                  )
                }
                error={errors.story_points?.message}
              />
            )}
          />
          <Input
            label="Story key"
            placeholder="PROJ-123"
            error={errors.external_id?.message}
            {...register("external_id")}
          />
          <Controller
            name="rank"
            control={control}
            render={({ field }) => (
              <Input
                label="Rank"
                type="number"
                min={0}
                value={field.value ?? ""}
                onChange={(e) =>
                  field.onChange(
                    e.target.value === "" ? null : Number(e.target.value)
                  )
                }
                error={errors.rank?.message}
              />
            )}
          />
        </div>
        <Input
          label="Sprint ID (optional)"
          error={errors.sprint_id?.message}
          {...register("sprint_id")}
        />
        {error ? (
          <p className="rounded-md bg-danger/5 px-3 py-2 text-sm text-danger">
            {getErrorMessage(error)}
          </p>
        ) : null}
      </form>
    </Modal>
  );
}
