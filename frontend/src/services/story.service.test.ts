/**
 * Story service unit tests (mocked axios)
 */

import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/axios", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

import { apiClient } from "@/lib/axios";
import { storyService } from "@/services/story.service";

const mockedClient = apiClient as unknown as {
  get: ReturnType<typeof vi.fn>;
  post: ReturnType<typeof vi.fn>;
  put: ReturnType<typeof vi.fn>;
  delete: ReturnType<typeof vi.fn>;
};

describe("storyService", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("lists stories with cleaned params", async () => {
    mockedClient.get.mockResolvedValue({
      data: {
        items: [],
        total: 0,
        page: 1,
        page_size: 10,
        total_pages: 0,
      },
    });

    await storyService.list({
      page: 1,
      page_size: 10,
      status: "draft",
      search: "",
      project_id: undefined,
    });

    expect(mockedClient.get).toHaveBeenCalledWith("/stories", {
      params: { page: 1, page_size: 10, status: "draft" },
    });
  });

  it("creates a story", async () => {
    const story = { id: "1", title: "New" };
    mockedClient.post.mockResolvedValue({ data: story });

    const result = await storyService.create({
      project_id: "550e8400-e29b-41d4-a716-446655440001",
      title: "New",
    });

    expect(result).toEqual(story);
    expect(mockedClient.post).toHaveBeenCalledWith("/stories", {
      project_id: "550e8400-e29b-41d4-a716-446655440001",
      title: "New",
    });
  });

  it("deletes a story", async () => {
    mockedClient.delete.mockResolvedValue({
      data: { success: true, message: "Story deleted successfully" },
    });

    const result = await storyService.remove("abc");
    expect(result.success).toBe(true);
    expect(mockedClient.delete).toHaveBeenCalledWith("/stories/abc");
  });
});
