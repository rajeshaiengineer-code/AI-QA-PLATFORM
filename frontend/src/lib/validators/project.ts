import { z } from "zod";

export const projectFormSchema = z.object({
  organization_id: z.string().uuid("Organization ID must be a valid UUID"),
  name: z.string().trim().min(1, "Name is required").max(255),
  key: z
    .string()
    .trim()
    .min(2, "Key must be at least 2 characters")
    .max(20)
    .regex(/^[A-Za-z0-9_-]+$/, "Key must be alphanumeric"),
  description: z.string().optional().nullable(),
  is_active: z.boolean(),
});

export type ProjectFormValues = z.infer<typeof projectFormSchema>;

export function toProjectPayload(values: ProjectFormValues) {
  return {
    organization_id: values.organization_id,
    name: values.name.trim(),
    key: values.key.trim().toUpperCase(),
    description: values.description?.trim() || null,
    is_active: values.is_active,
  };
}
