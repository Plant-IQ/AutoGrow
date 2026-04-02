"use client";
import { FormEvent, useState } from "react";
import { postJson } from "@/lib/api";

const initial = {
  height_cm: 20,
  leaf_count: 6,
  root_visible: false,
  canopy_score: 3,
};

export default function ObsForm() {
  const [values, setValues] = useState(initial);
  const [status, setStatus] = useState<"idle" | "saving" | "done" | "error">("idle");
  const [message, setMessage] = useState<string>("");

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setStatus("saving");
    setMessage("");

    try {
      const res = await postJson("/observations", values);

      if (!res.ok) throw new Error(await res.text());

      setStatus("done");
      setMessage("Saved");
      setValues(initial);
    } catch (err) {
      setStatus("error");
      setMessage("Could not save observation");
    }
  }

  function handleChange(field: string, value: number | boolean) {
    setValues((prev) => ({ ...prev, [field]: value }));
  }

  return (
    <form className="card gap-3" onSubmit={handleSubmit}>
      <p className="label">Add observation</p>
      <div className="grid grid-cols-2 gap-3">
        <label className="field">
          <span>Height (cm)</span>
          <input
            type="number"
            step="0.1"
            value={values.height_cm}
            onChange={(e) => handleChange("height_cm", parseFloat(e.target.value) || 0)}
          />
        </label>
        <label className="field">
          <span>Leaf count</span>
          <input
            type="number"
            value={values.leaf_count}
            onChange={(e) => handleChange("leaf_count", parseInt(e.target.value, 10) || 0)}
          />
        </label>
        <label className="field">
          <span>Canopy score (1-5)</span>
          <input
            type="number"
            min={1}
            max={5}
            value={values.canopy_score}
            onChange={(e) => handleChange("canopy_score", parseInt(e.target.value, 10) || 1)}
          />
        </label>
        <label className="field flex items-center gap-2">
          <input
            type="checkbox"
            checked={values.root_visible}
            onChange={(e) => handleChange("root_visible", e.target.checked)}
          />
          <span>Roots visible</span>
        </label>
      </div>
      <button
        type="submit"
        className="btn"
        disabled={status === "saving"}
      >
        {status === "saving" ? "Saving…" : "Save observation"}
      </button>
      {message && (
        <p className={`text-sm ${status === "error" ? "text-red-600" : "text-emerald-600"}`}>{message}</p>
      )}
    </form>
  );
}
