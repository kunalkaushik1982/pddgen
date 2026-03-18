import { fetchJson } from "./http";

export type AboutResponse = {
  app_name: string;
  environment: string;
  auth_provider: string;
  ai_provider: string;
  versions: {
    release: string;
    frontend: string;
    backend: string;
    worker: string;
  };
};

export const aboutService = {
  async getAbout(): Promise<AboutResponse> {
    return fetchJson<AboutResponse>("/meta/about");
  },
};
