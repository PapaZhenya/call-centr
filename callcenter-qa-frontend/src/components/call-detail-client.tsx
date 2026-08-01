"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { API_BASE_URL, ApiError, api, getAccessToken } from "@/lib/api-client";
import { speakerLabel } from "@/lib/format";
import type { Call, QAEvaluation, Transcript } from "@/lib/types";
import { ru } from "@/messages/ru";

const SPEAKER_LABELS = {
  agent: ru.callDetail.speakerAgent,
  customer: ru.callDetail.speakerCustomer,
  unknown: ru.callDetail.speakerUnknown,
  speakerN: ru.callDetail.speakerN,
};

export function CallDetailClient({ callId }: { callId: string }) {
  const [call, setCall] = useState<Call | null>(null);
  const [transcript, setTranscript] = useState<Transcript | null>(null);
  const [evaluation, setEvaluation] = useState<QAEvaluation | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement>(null);

  useEffect(() => {
    let cancelled = false;
    let objectUrl: string | null = null;

    async function load() {
      try {
        const callData = await api.get<Call>(`/api/v1/calls/${callId}`);
        if (cancelled) return;
        setCall(callData);

        // Audio requires the bearer token, so fetch it as a blob rather than
        // pointing <audio src> at a bare URL (which can't send headers).
        const token = getAccessToken();
        const audioResponse = await fetch(`${API_BASE_URL}/api/v1/calls/${callId}/audio`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        if (audioResponse.ok && !cancelled) {
          const blob = await audioResponse.blob();
          objectUrl = URL.createObjectURL(blob);
          setAudioUrl(objectUrl);
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof ApiError ? err.message : ru.common.error);
      }

      try {
        const transcriptData = await api.get<Transcript>(`/api/v1/calls/${callId}/transcript`);
        if (!cancelled) setTranscript(transcriptData);
      } catch {
        // transcript may not be ready yet - not worth surfacing as an error
      }

      try {
        const evaluationData = await api.get<QAEvaluation>(`/api/v1/calls/${callId}/qa`);
        if (!cancelled) setEvaluation(evaluationData);
      } catch {
        // evaluation may not be ready yet
      }
    }

    void load();
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [callId]);

  function seekTo(seconds: number) {
    if (audioRef.current) {
      audioRef.current.currentTime = seconds;
      void audioRef.current.play();
    }
  }

  return (
    <AppShell>
      <div className="stack">
        <Link href="/calls">← {ru.common.back}</Link>
        <h1>{call?.original_filename ?? callId}</h1>
        {error && <p className="error-text">{error}</p>}

        {audioUrl && (
          <div className="card">
            <audio ref={audioRef} controls src={audioUrl} style={{ width: "100%" }} />
          </div>
        )}

        <div className="grid">
          <div className="card stack">
            <h2>{ru.callDetail.transcript}</h2>
            {!transcript ? (
              <p className="muted">{ru.common.loading}</p>
            ) : (
              <div className="stack">
                {transcript.segments.map((segment, index) => (
                  <div
                    key={index}
                    className="transcript-segment"
                    role="button"
                    tabIndex={0}
                    onClick={() => seekTo(segment.start)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") seekTo(segment.start);
                    }}
                  >
                    <span className="speaker">{speakerLabel(segment.speaker, SPEAKER_LABELS)}</span>
                    <span className="muted">
                      {segment.start.toFixed(1)}s–{segment.end.toFixed(1)}s
                    </span>
                    <p style={{ margin: "4px 0 0" }}>{segment.text}</p>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="card stack">
            <h2>{ru.callDetail.qaResults}</h2>
            {!evaluation ? (
              <p className="muted">{ru.callDetail.noEvaluationYet}</p>
            ) : (
              <div className="stack">
                <p>
                  <strong>{ru.callDetail.overallScore}:</strong> {evaluation.overall_score ?? "—"}
                </p>
                {evaluation.notes && (
                  <p>
                    <strong>{ru.callDetail.notes}:</strong> {evaluation.notes}
                  </p>
                )}
                {evaluation.flags && evaluation.flags.length > 0 && (
                  <p>
                    <strong>{ru.callDetail.flags}:</strong>{" "}
                    {evaluation.flags.map((flag) => (
                      <span key={flag} className="badge danger" style={{ marginRight: 6 }}>
                        {flag}
                      </span>
                    ))}
                  </p>
                )}
                <div className="stack">
                  {evaluation.scores.map((score) => (
                    <div key={score.rubric_criterion_id} className="card" style={{ padding: 12 }}>
                      <div className="row" style={{ justifyContent: "space-between" }}>
                        <strong>{score.rubric_criterion.label}</strong>
                        <span className="badge">{score.score}</span>
                      </div>
                      <p className="muted" style={{ margin: "4px 0" }}>
                        {score.source === "rule"
                          ? ru.callDetail.sourceRule
                          : ru.callDetail.sourceLlm}
                      </p>
                      {score.rationale && <p style={{ margin: "4px 0" }}>{score.rationale}</p>}
                      {score.quote && (
                        <p className="muted" style={{ margin: "4px 0" }}>
                          {ru.callDetail.evidence}: «{score.quote}»
                          {score.evidence_start != null && (
                            <button
                              type="button"
                              className="secondary"
                              style={{ marginLeft: 8, padding: "2px 8px" }}
                              onClick={() => seekTo(score.evidence_start as number)}
                            >
                              ▶
                            </button>
                          )}
                        </p>
                      )}
                      {!score.quote && !score.quote_verified && (
                        <p className="muted">{ru.callDetail.quoteNotVerified}</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </AppShell>
  );
}
