"use client";

import { useEffect, useState, type FormEvent } from "react";
import { AppShell } from "@/components/app-shell";
import { ApiError, api } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { splitPhrases } from "@/lib/format";
import { RUBRIC_WRITE, hasPermission } from "@/lib/permissions";
import type { RubricCriterion, RubricVersion } from "@/lib/types";
import { ru } from "@/messages/ru";

async function reloadRubric(
  setCriteria: (criteria: RubricCriterion[]) => void,
  setVersions: (versions: RubricVersion[]) => void,
  setError: (message: string | null) => void,
) {
  try {
    const [criteriaData, versionsData] = await Promise.all([
      api.get<RubricCriterion[]>("/api/v1/rubric/criteria"),
      api.get<RubricVersion[]>("/api/v1/rubric/versions"),
    ]);
    setCriteria(criteriaData);
    setVersions(versionsData);
  } catch (err) {
    setError(err instanceof ApiError ? err.message : ru.common.error);
  }
}

export default function RubricPage() {
  const { user } = useAuth();
  const isAdmin = hasPermission(user, RUBRIC_WRITE);

  const [criteria, setCriteria] = useState<RubricCriterion[]>([]);
  const [versions, setVersions] = useState<RubricVersion[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [key, setKey] = useState("");
  const [label, setLabel] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("");
  const [maxScore, setMaxScore] = useState(5);
  const [isCritical, setIsCritical] = useState(false);
  const [requiredPhrases, setRequiredPhrases] = useState("");
  const [forbiddenPhrases, setForbiddenPhrases] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  const [selectedCriteria, setSelectedCriteria] = useState<Record<string, boolean>>({});
  const [versionName, setVersionName] = useState("");

  // Inline phrase editor state for one criterion row at a time.
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editRequired, setEditRequired] = useState("");
  const [editForbidden, setEditForbidden] = useState("");
  const [isSavingPhrases, setIsSavingPhrases] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [criteriaData, versionsData] = await Promise.all([
          api.get<RubricCriterion[]>("/api/v1/rubric/criteria"),
          api.get<RubricVersion[]>("/api/v1/rubric/versions"),
        ]);
        if (!cancelled) {
          setCriteria(criteriaData);
          setVersions(versionsData);
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof ApiError ? err.message : ru.common.error);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleCreateCriterion(event: FormEvent) {
    event.preventDefault();
    setIsSaving(true);
    setError(null);
    try {
      await api.post("/api/v1/rubric/criteria", {
        key,
        label,
        description,
        category: category || null,
        max_score: maxScore,
        is_critical: isCritical,
        required_phrases: splitPhrases(requiredPhrases),
        forbidden_phrases: splitPhrases(forbiddenPhrases),
      });
      setKey("");
      setLabel("");
      setDescription("");
      setCategory("");
      setMaxScore(5);
      setIsCritical(false);
      setRequiredPhrases("");
      setForbiddenPhrases("");
      await reloadRubric(setCriteria, setVersions, setError);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : ru.common.error);
    } finally {
      setIsSaving(false);
    }
  }

  function startEditPhrases(criterion: RubricCriterion) {
    setEditingId(criterion.id);
    setEditRequired(criterion.required_phrases?.join(", ") ?? "");
    setEditForbidden(criterion.forbidden_phrases?.join(", ") ?? "");
  }

  async function handleSavePhrases(criterionId: string) {
    setIsSavingPhrases(true);
    setError(null);
    try {
      // splitPhrases returns null for an empty input - an explicit null in the
      // PATCH clears the list and turns the criterion back into LLM-scored.
      await api.patch(`/api/v1/rubric/criteria/${criterionId}`, {
        required_phrases: splitPhrases(editRequired),
        forbidden_phrases: splitPhrases(editForbidden),
      });
      setEditingId(null);
      await reloadRubric(setCriteria, setVersions, setError);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : ru.common.error);
    } finally {
      setIsSavingPhrases(false);
    }
  }

  async function handleCreateVersion(event: FormEvent) {
    event.preventDefault();
    const chosen = Object.entries(selectedCriteria)
      .filter(([, checked]) => checked)
      .map(([id]) => ({ rubric_criterion_id: id, weight: 1.0 }));
    if (chosen.length === 0 || !versionName) return;
    setError(null);
    try {
      await api.post("/api/v1/rubric/versions", {
        name: versionName,
        llm_model_id: "local",
        criteria: chosen,
      });
      setVersionName("");
      setSelectedCriteria({});
      await reloadRubric(setCriteria, setVersions, setError);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : ru.common.error);
    }
  }

  async function handleActivate(versionId: string) {
    try {
      await api.post(`/api/v1/rubric/versions/${versionId}/activate`);
      await reloadRubric(setCriteria, setVersions, setError);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : ru.common.error);
    }
  }

  return (
    <AppShell>
      <div className="stack">
        <h1>{ru.rubric.title}</h1>
        {error && <p className="error-text">{error}</p>}
        {!isAdmin && <p className="muted">{ru.rubric.adminOnly}</p>}

        <div className="card stack">
          <h2>{ru.rubric.criteria}</h2>
          <table>
            <thead>
              <tr>
                <th>{ru.rubric.key}</th>
                <th>{ru.rubric.label}</th>
                <th>{ru.rubric.category}</th>
                <th>{ru.rubric.maxScore}</th>
                <th>{ru.rubric.isCritical}</th>
                <th>{ru.rubric.requiredPhrases}</th>
                <th>{ru.rubric.forbiddenPhrases}</th>
                {isAdmin && <th />}
              </tr>
            </thead>
            <tbody>
              {criteria.map((c) => (
                <tr key={c.id}>
                  <td>{c.key}</td>
                  <td>{c.label}</td>
                  <td>{c.category ?? "—"}</td>
                  <td>{c.max_score}</td>
                  <td>{c.is_critical ? "✓" : ""}</td>
                  {editingId === c.id ? (
                    <>
                      <td>
                        <input
                          aria-label={ru.rubric.requiredPhrases}
                          value={editRequired}
                          onChange={(e) => setEditRequired(e.target.value)}
                        />
                      </td>
                      <td>
                        <input
                          aria-label={ru.rubric.forbiddenPhrases}
                          value={editForbidden}
                          onChange={(e) => setEditForbidden(e.target.value)}
                        />
                      </td>
                      <td>
                        <div className="row" style={{ gap: 6 }}>
                          <button
                            type="button"
                            disabled={isSavingPhrases}
                            onClick={() => void handleSavePhrases(c.id)}
                          >
                            {ru.common.save}
                          </button>
                          <button
                            type="button"
                            className="secondary"
                            onClick={() => setEditingId(null)}
                          >
                            {ru.common.cancel}
                          </button>
                        </div>
                      </td>
                    </>
                  ) : (
                    <>
                      <td>{c.required_phrases?.join(", ") ?? "—"}</td>
                      <td>{c.forbidden_phrases?.join(", ") ?? "—"}</td>
                      {isAdmin && (
                        <td>
                          <button
                            type="button"
                            className="secondary"
                            onClick={() => startEditPhrases(c)}
                          >
                            {ru.common.edit}
                          </button>
                        </td>
                      )}
                    </>
                  )}
                </tr>
              ))}
            </tbody>
          </table>

          {isAdmin && (
            <form className="stack" onSubmit={handleCreateCriterion}>
              <h3>{ru.rubric.newCriterion}</h3>
              <div className="grid">
                <div className="field">
                  <label htmlFor="key">{ru.rubric.key}</label>
                  <input id="key" required value={key} onChange={(e) => setKey(e.target.value)} />
                </div>
                <div className="field">
                  <label htmlFor="label">{ru.rubric.label}</label>
                  <input
                    id="label"
                    required
                    value={label}
                    onChange={(e) => setLabel(e.target.value)}
                  />
                </div>
                <div className="field">
                  <label htmlFor="category">{ru.rubric.category}</label>
                  <input
                    id="category"
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                  />
                </div>
                <div className="field">
                  <label htmlFor="maxScore">{ru.rubric.maxScore}</label>
                  <input
                    id="maxScore"
                    type="number"
                    min={2}
                    max={10}
                    value={maxScore}
                    onChange={(e) => setMaxScore(Number(e.target.value))}
                  />
                </div>
                <div className="field">
                  <label htmlFor="isCritical">{ru.rubric.isCritical}</label>
                  <input
                    id="isCritical"
                    type="checkbox"
                    checked={isCritical}
                    onChange={(e) => setIsCritical(e.target.checked)}
                  />
                </div>
              </div>
              <div className="field">
                <label htmlFor="description">{ru.rubric.description}</label>
                <textarea
                  id="description"
                  required
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                />
              </div>
              <div className="grid">
                <div className="field">
                  <label htmlFor="requiredPhrases">{ru.rubric.requiredPhrases}</label>
                  <input
                    id="requiredPhrases"
                    value={requiredPhrases}
                    onChange={(e) => setRequiredPhrases(e.target.value)}
                  />
                </div>
                <div className="field">
                  <label htmlFor="forbiddenPhrases">{ru.rubric.forbiddenPhrases}</label>
                  <input
                    id="forbiddenPhrases"
                    value={forbiddenPhrases}
                    onChange={(e) => setForbiddenPhrases(e.target.value)}
                  />
                </div>
              </div>
              <div>
                <button type="submit" disabled={isSaving}>
                  {ru.rubric.save}
                </button>
              </div>
            </form>
          )}
        </div>

        <div className="card stack">
          <h2>{ru.rubric.versions}</h2>
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>{ru.rubric.versionName}</th>
                <th>{ru.rubric.active}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {versions.map((v) => (
                <tr key={v.id}>
                  <td>{v.version_number}</td>
                  <td>{v.name}</td>
                  <td>
                    <span className={`badge ${v.is_active ? "success" : "muted"}`}>
                      {v.is_active ? ru.rubric.active : ru.rubric.inactive}
                    </span>
                  </td>
                  <td>
                    {isAdmin && !v.is_active && (
                      <button
                        type="button"
                        className="secondary"
                        onClick={() => void handleActivate(v.id)}
                      >
                        {ru.rubric.activate}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {isAdmin && (
            <form className="stack" onSubmit={handleCreateVersion}>
              <h3>{ru.rubric.createVersion}</h3>
              <div className="field">
                <label htmlFor="versionName">{ru.rubric.versionName}</label>
                <input
                  id="versionName"
                  required
                  value={versionName}
                  onChange={(e) => setVersionName(e.target.value)}
                />
              </div>
              <div className="stack">
                {criteria.map((c) => (
                  <label key={c.id} className="row" style={{ gap: 8 }}>
                    <input
                      type="checkbox"
                      checked={Boolean(selectedCriteria[c.id])}
                      onChange={(e) =>
                        setSelectedCriteria((prev) => ({ ...prev, [c.id]: e.target.checked }))
                      }
                    />
                    {c.label}
                  </label>
                ))}
              </div>
              <div>
                <button type="submit">{ru.rubric.createVersion}</button>
              </div>
            </form>
          )}
        </div>
      </div>
    </AppShell>
  );
}
