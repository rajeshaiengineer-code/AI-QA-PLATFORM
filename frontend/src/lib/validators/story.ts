/**
 * Zod validators for Story create / update forms
 */

import { z } from "zod";

export const storyFormSchema = z.object({
  project_id: z.string().trim().uuid("Project ID must be a valid UUID"),
  title: z
    .string()
    .trim()
    .min(1, "Title is required")
    .max(500, "Title must be at most 500 characters"),
  description: z.string().optional().nullable(),
  status: z.enum([
    "draft",
    "ready",
    "in_progress",
    "in_review",
    "done",
    "blocked",
  ]),
  story_type: z.enum(["feature", "bug", "task", "spike", "enhancement"]),
  priority: z.enum(["critical", "high", "medium", "low"]),
  story_points: z.number().int().min(0).max(100).nullable().optional(),
  external_id: z.string().max(100).nullable().optional(),
  rank: z.number().int().min(0).nullable().optional(),
  sprint_id: z
    .string()
    .optional()
    .nullable()
    .refine(
      (value) => !value || z.string().uuid().safeParse(value).success,
      "Sprint ID must be a valid UUID"
    ),
});

export type StoryFormValues = z.infer<typeof storyFormSchema>;

/** Normalize optional blank strings before API submit. */
export function toStoryPayload(values: StoryFormValues) {
  const sprint = values.sprint_id?.trim();
  const external = values.external_id?.trim();
  const description = values.description?.trim();

  return {
    project_id: values.project_id.trim(),
    title: values.title.trim(),
    description: description ? description : null,
    status: values.status,
    story_type: values.story_type,
    priority: values.priority,
    story_points: values.story_points ?? null,
    external_id: external ? external : null,
    rank: values.rank ?? null,
    sprint_id: sprint ? sprint : null,
  };
}
