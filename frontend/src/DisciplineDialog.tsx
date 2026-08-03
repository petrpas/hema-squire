import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { type DisciplineGender, type DisciplineKind, type DisciplineMaterial } from "./api";
import HelpHint from "./HelpHint";
import { LEGACY_WEAPONS, disciplineName, normalizeSlug, taxonomyCode } from "./TournamentFace";

const TAXONOMY_WEAPON_CODES = Object.keys(LEGACY_WEAPONS);
const OTHER_WEAPON = "__other__";

// The dialog owns exactly the fields that freeze together (design
// discipline-identity-modal D1) — nothing else.
export interface DisciplineIdentity {
  kind: DisciplineKind;
  weapon: string;
  weaponCustom: boolean;
  gender: DisciplineGender;
  material: DisciplineMaterial;
  name: string;
  slug: string;
}

/** Port of `generate_slug` (`backend/app/routers/tournaments.py`) for the
 * dialog's own live preview — the dialog always sends an explicit slug, so
 * the backend generator is a fallback for non-console callers only (design
 * D3), and this is the frontend's equivalent. */
function generateDraftSlug(
  existingSlugs: Set<string>,
  kind: DisciplineKind,
  weapon: string,
  gender: DisciplineGender,
  material: DisciplineMaterial,
): string {
  const base = normalizeSlug(taxonomyCode(weapon, gender, material)) || "Discipline";
  const prefixed = kind === "team" ? `Team-${base}` : base;
  if (!existingSlugs.has(prefixed)) return prefixed;
  let counter = 2;
  while (existingSlugs.has(`${prefixed}-${counter}`)) counter++;
  return `${prefixed}-${counter}`;
}

/** The name and slug a classification derives on its own, with no collision
 * counter — the comparison basis for deciding whether a stored value was
 * overridden (design discipline-identity-modal / refine-detail-and-setup-ui
 * D5). Unlike `generateDraftSlug`, this never disambiguates against other
 * rows, so a legitimately generated `LS-2` is not misread as an override. */
function deriveIdentity(
  kind: DisciplineKind,
  weapon: string,
  gender: DisciplineGender,
  material: DisciplineMaterial,
): { name: string; slug: string } {
  const name = disciplineName(weapon, gender, material, kind === "team") ?? "";
  if (!weapon) return { name, slug: "" };
  const base = normalizeSlug(taxonomyCode(weapon, gender, material)) || "Discipline";
  const slug = kind === "team" ? `Team-${base}` : base;
  return { name, slug };
}

function initialTouched(initial: DisciplineIdentity | null): { name: boolean; slug: boolean } {
  if (!initial) return { name: false, slug: false };
  const derived = deriveIdentity(initial.kind, initial.weapon, initial.gender, initial.material);
  return { name: initial.name !== derived.name, slug: initial.slug !== derived.slug };
}

export default function DisciplineDialog({
  initial,
  otherNames,
  otherSlugs,
  onConfirm,
  onClose,
}: {
  /** null adds a new discipline; non-null reopens an existing one. */
  initial: DisciplineIdentity | null;
  /** Every other row's name in the table, saved or merely drafted. */
  otherNames: string[];
  /** Every other row's slug in the table, saved or merely drafted. */
  otherSlugs: Set<string>;
  onConfirm: (value: DisciplineIdentity) => void;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const [kind, setKind] = useState<DisciplineKind>(initial?.kind ?? "individual");
  const [material, setMaterial] = useState<DisciplineMaterial>(initial?.material ?? "");
  const [weaponCustom, setWeaponCustom] = useState(initial?.weaponCustom ?? false);
  const [weapon, setWeapon] = useState(initial?.weapon ?? "");
  const [gender, setGender] = useState<DisciplineGender>(initial?.gender ?? "");
  const [name, setName] = useState(initial?.name ?? "");
  const [slug, setSlug] = useState(initial?.slug ?? "");
  // Independent per-field flags: derivation runs until the organizer types
  // into that field, then stops for that field alone (design D3). For a new
  // discipline both start false; for a reopened one, each starts true when
  // the stored value is not what its stored classification would derive
  // (design D5), so an override is not recaptured by a later classification
  // change while a generated value keeps tracking it.
  const [nameTouched, setNameTouched] = useState(() => initialTouched(initial).name);
  const [slugTouched, setSlugTouched] = useState(() => initialTouched(initial).slug);
  const [error, setError] = useState<string | null>(null);
  // A reopened dialog's first effect run must not overwrite the loaded
  // values before the touched flags above have had a chance to matter.
  const skipFirstDerivation = useRef(initial !== null);

  useEffect(() => {
    if (skipFirstDerivation.current) {
      skipFirstDerivation.current = false;
      return;
    }
    if (!nameTouched) {
      setName(disciplineName(weapon, gender, material, kind === "team") ?? "");
    }
    if (!slugTouched) {
      setSlug(weapon ? generateDraftSlug(otherSlugs, kind, weapon, gender, material) : "");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [kind, weapon, gender, material]);

  const trimmedName = name.trim();
  const duplicateName =
    trimmedName !== "" &&
    otherNames.some((other) => other.trim().toLowerCase() === trimmedName.toLowerCase());

  function confirm() {
    const weaponValue = weaponCustom ? weapon.trim() : weapon;
    if (!weaponValue) {
      setError(t("setup.disciplineDialog.weaponRequired"));
      return;
    }
    if (weaponCustom && !trimmedName) {
      setError(t("setup.disciplineDialog.nameRequired"));
      return;
    }
    const finalName =
      trimmedName || disciplineName(weaponValue, gender, material, kind === "team") || "";
    const normalizedSlug =
      normalizeSlug(slug) || generateDraftSlug(otherSlugs, kind, weaponValue, gender, material);
    if (otherSlugs.has(normalizedSlug)) {
      setError(t("setup.disciplineDialog.slugTaken", { slug: normalizedSlug }));
      return;
    }
    onConfirm({
      kind,
      weapon: weaponValue,
      weaponCustom,
      gender,
      material,
      name: finalName,
      slug: normalizedSlug,
    });
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(event) => event.stopPropagation()}>
        <h2>
          {t(initial ? "setup.disciplineDialog.editTitle" : "setup.disciplineDialog.addTitle")}
        </h2>
        <div className="form-fields">
          <label className="form-field">
            <span>{t("setup.disciplines.kind")}</span>
            <select value={kind} onChange={(event) => setKind(event.target.value as DisciplineKind)}>
              <option value="individual">{t("setup.disciplines.kindIndividual")}</option>
              <option value="team">{t("setup.disciplines.kindTeam")}</option>
            </select>
          </label>
          <label className="form-field">
            <span>{t("setup.disciplines.material")}</span>
            <select
              value={material}
              onChange={(event) => setMaterial(event.target.value as DisciplineMaterial)}
            >
              <option value="">{t("setup.disciplines.materialSteel")}</option>
              <option value="Plastic">{t("setup.disciplines.materialPlastic")}</option>
            </select>
          </label>
          <label className="form-field">
            <span>{t("setup.disciplines.weapon")}</span>
            <select
              value={weaponCustom ? OTHER_WEAPON : weapon}
              onChange={(event) => {
                const value = event.target.value;
                if (value === OTHER_WEAPON) {
                  setWeaponCustom(true);
                  setWeapon("");
                } else {
                  setWeaponCustom(false);
                  setWeapon(value);
                }
              }}
            >
              <option value="">—</option>
              {TAXONOMY_WEAPON_CODES.map((code) => (
                <option key={code} value={code}>
                  {LEGACY_WEAPONS[code]}
                </option>
              ))}
              <option value={OTHER_WEAPON}>{t("setup.disciplines.weaponOther")}</option>
            </select>
          </label>
          {weaponCustom && (
            <label className="form-field">
              <span>{t("setup.disciplines.weaponOther")}</span>
              <input
                autoFocus
                value={weapon}
                onChange={(event) => setWeapon(event.target.value)}
              />
              <span className="muted">{t("setup.disciplines.weaponNoRatingHint")}</span>
            </label>
          )}
          <label className="form-field">
            <span>{t("setup.disciplines.gender")}</span>
            <select
              value={gender}
              onChange={(event) => setGender(event.target.value as DisciplineGender)}
            >
              <option value="">{t("setup.disciplines.genderOpen")}</option>
              <option value="W">{t("setup.disciplines.genderWomen")}</option>
              <option value="M">{t("setup.disciplines.genderMen")}</option>
            </select>
          </label>
          <hr className="modal-rule" />
          <label className="form-field">
            <span>{t("setup.disciplines.name")}</span>
            <input
              value={name}
              placeholder={weaponCustom ? undefined : t("setup.disciplines.nameAuto")}
              onChange={(event) => {
                setNameTouched(true);
                setName(event.target.value);
              }}
            />
          </label>
          {duplicateName && (
            <p className="login-error">{t("setup.disciplineDialog.duplicateName")}</p>
          )}
          <label className="form-field">
            <span>
              {t("setup.disciplines.slug")}
              <HelpHint text={t("setup.disciplines.slugHint")} />
            </span>
            <input
              value={slug}
              placeholder={t("setup.disciplines.slugAuto")}
              onChange={(event) => {
                setSlugTouched(true);
                setSlug(event.target.value);
              }}
            />
          </label>
        </div>
        {error && <p className="login-error">{error}</p>}
        <div className="modal-actions">
          <button type="button" className="secondary" onClick={onClose}>
            {t("common.cancel")}
          </button>
          <button type="button" className="btn-primary" onClick={confirm}>
            {t("setup.disciplineDialog.confirm")}
          </button>
        </div>
      </div>
    </div>
  );
}
