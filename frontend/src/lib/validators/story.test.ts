/**
 * Zod schema unit tests for Story forms
 */

import { describe, expect, it } from "vitest";

import { storyFormSchema, toStoryPayload } from "@/lib/validators/story";

describe("storyFormSchema", () => {
  it("accepts a valid create payload", () => {
    const result = storyFormSchema.safeParse({
      project_id: "550e8400-e29b-41d4-a716-446655440001",
      title: "User can reset password",
      description: "As a user...",
      status: "draft",
      story_type: "feature",
      priority: "medium",
      story_points: 3,
      external_id: "PROJ-1",
      rank: 1,
      sprint_id: "",
    });

    expect(result.success).toBe(true);
  });

  it("normalizes blank optional fields for API", () => {
    const payload = toStoryPayload({
      project_id: "550e8400-e29b-41d4-a716-446655440001",
      title: " User can reset password ",
      description: "",
      status: "draft",
      story_type: "feature",
      priority: "medium",
      story_points: null,
      external_id: "  ",
      rank: null,
      sprint_id: "",
    });

    expect(payload.description).toBeNull();
    expect(payload.external_id).toBeNull();
    expect(payload.sprint_id).toBeNull();
    expect(payload.title).toBe("User can reset password");
  });

  it("rejects blank title", () => {
    const result = storyFormSchema.safeParse({
      project_id: "550e8400-e29b-41d4-a716-446655440001",
      title: "   ",
      status: "draft",
      story_type: "feature",
      priority: "medium",
    });
    expect(result.success).toBe(false);
  });

  it("rejects invalid project_id", () => {
    const result = storyFormSchema.safeParse({
      project_id: "not-a-uuid",
      title: "Valid title",
      status: "draft",
      story_type: "feature",
      priority: "medium",
    });
    expect(result.success).toBe(false);
  });
});
