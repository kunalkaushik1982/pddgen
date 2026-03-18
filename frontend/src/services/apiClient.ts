import { artifactService } from "./artifactService";
import { authService } from "./authService";
import { diagramService } from "./diagramService";
import { exportService } from "./exportService";
import { sessionService } from "./sessionService";
import { uploadService } from "./uploadService";

export const apiClient = {
  ...authService,
  ...sessionService,
  ...uploadService,
  ...diagramService,
  ...exportService,
  ...artifactService,
};
