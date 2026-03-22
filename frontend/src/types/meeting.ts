/**
 * Purpose: Frontend meeting types for multi-meeting sessions.
 * Full filepath: C:\Users\work\Documents\PddGenerator\frontend\src\types\meeting.ts
 */

export type Meeting = {
  id: string;
  sessionId: string;
  title: string;
  meetingDate: string | null;
  uploadedAt: string;
  orderIndex: number | null;
};

