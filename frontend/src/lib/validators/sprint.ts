import { z } from "zod";

export const sprintFormSchema = z
  .object({
    project_id: z.string().uuid("Project ID must be a valid UUID"),
    name: z.string().trim().min(1, "Name is required").max(255),
    goal: z.string().optional().nullable(),
    start_date: z.string().optional().nullable(),
    end_date: z.string().optional().nullable(),
    is_active: z.boolean(),
  })
  .refine(
    (data) => {
      if (data.start_date && data.end_date) {
        return data.end_date >= data.start_date;
      }
      return true;
    },
    { message: "End date must be on or after start date", path: ["end_date"] }
  );

export type SprintFormValues = z.infer<typeof sprintFormSchema>;

export function toSprintPayload(values: SprintFormValues) {
  return {
    project_id: values.project_id,
    name: values.name.trim(),
    goal: values.goal?.trim() || null,
    start_date: values.start_date || null,
    end_date: values.end_date || null,
    is_active: values.is_active,
  };
}
