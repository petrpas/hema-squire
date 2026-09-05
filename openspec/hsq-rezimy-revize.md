# HSQ: revize specky proti řezu automatický / manuální režim

Podklad z větve `payments-work` (HEAD `6b7afd5`), 27 živých capabilities v `openspec/specs/`,
5 neuzavřených changes v `openspec/changes/`. Názvy capabilities a requirementů jsou ponechány
anglicky, jak jsou v repu.

---

## 1. Nálezy, které mění zadání

### 1.1 Slovo "mode" je obsazené a znamená něco jiného

`tournament-modes` už existuje a definuje **čtyři nezávislé feature flagy** — `schedule`,
`payments`, `team disciplines`, `extra services`. "Easy mode" je jméno pro stav, kdy není
zapnutý žádný, "advanced mode" pro stav, kdy je zapnutý aspoň jeden. Spec explicitně říká, že
žádná samostatná hodnota režimu se neukládá:

> There SHALL be no separately stored mode value, so the name a tournament is given and the
> sections its console offers SHALL never disagree.

Automatický / manuální je **jiná osa**. Kdyby se přidal jako pátý flag, porušil by pravidlo, na
kterém ta capability stojí — *"Disabling a feature hides its settings without changing them"* —
protože manuální režim nemá skrývat nastavení, má měnit vlastnictví seznamu a vypnout autonomii.

Jedinou výjimkou z toho pravidla je dnes `payments`, který má vlastní requirement *"The payments
feature suspends the payment machinery"*. To je precedens, ale je to precedens jedné výjimky, ne
vzor k opakování.

**Doporučení:** nová osa se ukládá samostatně a nejmenuje se "mode". Návrh pojmenování:
`registration_ownership` ∈ {`SQUIRE`, `ORGANIZER`}, česky *registrace vede Squire* / *registrace
vede organizátor*. Existující easy/advanced nechat být, je odbavené v UI, v dialogu i v `cs.json`.

### 1.2 Manuální režim je z větší části postavený, jen nemá jméno

Rozdělení, které navrhuješ, v repu de facto už je, jen prochází napříč capabilities místo aby
bylo pojmenované:

| Větev | Co ji dnes tvoří |
|---|---|
| manuální | `table-import`, `edit-rules`, `etl-console`, `console-operations`, `hr-integration`, `data-export` |
| automatická | `registration`, `fencer-home`, `fencer-accounts`, `seating-queue`, `tournament-publication`, scheduler |
| sdílené | `payments`, `tournament-admin`, `setup-navigation`, `design-system`, `localization`, `field-validation`, `routing`, `responsive-layout` |

Dvě věci, které jsem navrhoval v předchozím kole, existují a není potřeba je znovu vymýšlet:

- **override vrstva s proveniencí** = `edit-rules` (*"Every manual action creates a rule"*,
  *"Deterministic replay"*) plus `etl-console` (*"Two manual-edits logs with two meanings"*,
  *"Readable manual-edits log"*).
- **záznam osoby bez účtu** = už je spec'd v `issue-imported-registrations`, delta na
  `fencer-accounts`: fencer record bez credentials, bez pozvánky, bez mailu.

### 1.3 Obě větve už se srazily; to místo se jmenuje `issue-imported-registrations`

Ta change bere importované řádky a vyrábí z nich `Fencer` bez účtu a **plnohodnotné
`Registration` s VS**, naceněné a zmrazené, s "dormant clocks". Její vlastní risk sekce to
pojmenovává přesně:

> A registration that reaches `scheduler.py` without it opens a payment window and sends expiry
> and reminder mail to people who registered a year ago.

To je per-row únikový poklop proti scheduleru. Mode na úrovni turnaje by byl **strukturální**
obrana: scheduler by se na turnaje s `ORGANIZER` vůbec nedíval. Per-row značka je pak stále
potřeba (doregistrace klubu do jinak automatického turnaje), ale přestává být jedinou pojistkou.

### 1.4 "Dormant" má dnes dvě příčiny, chystá se třetí

1. `registration` → *"Both clocks SHALL be dormant while the tournament's payments feature is off"*
2. `issue-imported-registrations` → dormant **by origin**, trvale
3. manuální režim by přidal třetí

Tři nezávislé podmínky ve `scheduler.py` a v `_reminder_due` znamenají osminásobnou testovací
matici na to, aby se nerozeslalo 54 mailů. **Sjednotit do jednoho odvozeného predikátu** (např.
`registration.squire_collects`) s uloženým důvodem pro čitelnost, a scheduler nechat konzultovat
výhradně ten. Testuje se jeden predikát a jeden dotaz scheduleru, ne tři cesty.

---

## 2. Tvoje tři korekce proti reálné specce

### 2.1 Publikace a veřejný list pro oba režimy

- `tournament-publication` je už dnes na režimu nezávislá, beze změny.
- `registration` → *"Public participant list"* říká, že list ukazuje **confirmed (paid)**
  registrace a nezaplacené buď skrývá, nebo šedí. V manuálním režimu (a v jakémkoli turnaji
  s `payments` off) nemá "confirmed" význam. Potřebuje vlastní pravidlo pro režim, kde stav
  platby neexistuje nebo ho Squire negarantuje.
- **Odkaz na externí formulář v repu neexistuje.** Grep přes `specs/` na `external
  registration` / `registration_url` vrací jen `table-import`. Je to nové pole, ne rekonfigurace
  existujícího.
- `tournament-admin` → *"Setup completeness"* dnes podmiňuje bankovní účet stavem `payments`.
  V manuálním režimu je povinnou položkou místo toho URL externího formuláře, a `registration
  window` přestává mít smysl jako vynucovaný údaj.

### 2.2 CRUD v automatu, který přežije rerun

Tady je formulace zavádějící a stojí za přeformulování dřív, než se z ní udělá requirement.
V automatickém režimu **žádný rerun neexistuje** — `etl-console`'s *"Rerun"* a `edit-rules`'s
*"Deterministic replay"* běží nad importovanými sheet rows, ne nad in-app registracemi. Věta
"změna přežije rerun" je tam splněná triviálně, protože se nemá co spustit.

Skutečná otázka v automatickém režimu je **precedence org overridu proti třem jiným zapisovatelům**:

1. šermíř sám (`registration` → *"Registration amendment"*, `fencer-home` → *"Registration management"*)
2. matching plateb (kredit, tolerance, `likely` proposals)
3. lifecycle (`seating settlement`, expiry, demote do fronty)

Ve specce to není nikde. To je reálná mezera a je to jediná podstatná nová věc, kterou k tomu
řezu musíš vymyslet. Návrh pravidel:

- ruční hodnota organizátora má přednost před šermířovou editací téhož pole; šermíř dostane
  informaci, ne tichý přepis
- ruční nastavení stavu (odhlášen, zaplaceno) nesmí být zrušeno lifecyklem; expiry ani seating
  settlement se overridnuté registrace nedotkne
- platba dorazivší na ručně odhlášenou registraci nekřísí nic, padá do fronty výjimek
  (dnes by prošla `payments` → *"Payments arriving after expiry"*, což je jiný případ)

### 2.3 Ruční upload výpisu v automatu

Hotové. `add-payments-intake` dělá statement import bank-agnostic (LLM tvaruje libovolné
CSV/XLSX, Fio si drží deterministický parser podle hlavičky `ID pohybu`) a intake karta nabízí
upload i *poll Fio now* nezávisle na režimu.

Chybí jen tvůj constraint. Dnes `tournament-admin` → *"Payment and reservation parameters"*
nabízí tři payment mode hodnoty bez ohledu na to, odkud výpis chodí:

- `immediate payment`
- `reservation with deposit`
- `reservation without deposit`

Přidat pravidlo: **`reservation with deposit` vyžaduje nakonfigurovaný `fio_token`.** Bez API
feedu zůstává `immediate payment` a `reservation without deposit`, obojí splatné k jedné
`seating deadline`, což s dávkovými platbami funguje, protože kontrola je jednorázová po
termínu, ne průběžná. Turnaj tím neztrácí upomínky ani potvrzení, ztrácí klouzavé okno per
registrace.

---

## 3. Rozdělení capabilities

### Sdílené, beze změny

`design-system`, `localization`, `field-validation`, `responsive-layout`, `routing`,
`organizer-prose`, `setup-field-suggestions`, `setup-preview`, `discipline-identity`,
`hr-integration`, `console-operations`, `data-export`, `tournament-publication`.

### Sdílené, s režimem jako podmínkou uvnitř

| Capability | Co se mění |
|---|---|
| `tournament-admin` | nové pole external registration URL; `Setup completeness` větví povinné položky podle režimu; `Payment and reservation parameters` dostává vazbu payment mode × payment feed |
| `setup-navigation` | `Section allocation to tabs` — v manuálním režimu odpadají sekce, které nikdo neobsluhuje (registration window, reminder day) |
| `payments` | `Reconciliation applies only where payments are enabled` se rozšiřuje o práh potvrzení: v manuálním režimu je nekonečný, všechno jde do fronty k potvrzení |
| `etl-console` | Fencers phase a CRUD platí v obou režimech (dnes už tak fungují: `Import tab SHALL show imported rows alone`, in-app registrace jsou jinde); Payments phase se v manuálním režimu drží, ale bez lifecycle akcí |
| `edit-rules` | beze změny mechaniky, přibývá pravidlo precedence org overridu proti šermíři a proti lifecyklu (viz 2.2) |

### Jen automatický režim

`registration` (celý stavový automat, reservation lifecycle, payment window, capacity a
substitutes, confirmation email, price preview), `fencer-home`, `fencer-accounts` ve své
self-service části, `seating-queue`, `team-disciplines` v části, kde šermíř sestavuje roster,
scheduler jako celek.

### Jen manuální režim

`table-import` v celém rozsahu, `imported-registrations` (nová, viz níže), external registration
URL na veřejné stránce místo tlačítka Register, export platebních podkladů pro vlastní mailing,
migrace do automatického režimu.

---

## 4. Requirement-level seznam změn

**Nová capability** `registration-ownership`: co je uloženo, kdy se volí, co manuální režim
nesmí (žádný scheduler, žádná vazba na účet šermíře, žádné automatické maily), jak se přechází
do automatického.

**Modified:**

| Capability | Requirement | Změna |
|---|---|---|
| `tournament-admin` | Tournament definition | + external registration URL |
| `tournament-admin` | Setup completeness | povinné položky větví podle režimu |
| `tournament-admin` | Payment and reservation parameters | deposit mode vyžaduje Fio token |
| `tournament-admin` | Registration window | v manuálním režimu informativní, ne vynucovaná |
| `registration` | Public participant list | list pro režim bez garantovaného stavu platby, s uvedením čerstvosti podkladů |
| `registration` | Reservation lifecycle | tři příčiny dormance sjednotit do jednoho predikátu |
| `registration` | Registration availability | v manuálním režimu se in-app registrace nikdy neotevírá |
| `fencer-home` | Fencer Home landing | karta manuálního turnaje nabízí odkaz ven, ne Register |
| `fencer-home` | Registration with live total | neplatí pro manuální režim |
| `fencer-home` | Mine tab | manuální turnaj se v Mine neobjeví, protože registrace není v HSQ |
| `payments` | Automatic matching outcome | práh potvrzení jako parametr režimu |
| `edit-rules` | *(nový)* Precedence of a manual override | org override vs. šermíř vs. lifecycle |
| `etl-console` | Manual entry of a fencer | zůstává; propojit s issuing akcí, jak už dělá `issue-imported-registrations` |
| `tournament-modes` | Purpose | dovětek, že čtyři features jsou jiná osa než vlastnictví registrací |

---

## 5. Pořadí

1. **`registration_ownership` jako pole + volba při založení + vyloučení scheduleru.** Malé,
   a dělá to z per-row značky v `issue-imported-registrations` druhou pojistku místo jediné.
2. **Sjednocení predikátu dormance.** Dělat před tím, než přibude třetí příčina, ne po.
3. `issue-imported-registrations` a `add-name-assisted-payment-matching` dokončit beze změny
   plánu — pilot `na-duel-2026` s 54 řádky a 43 transakcemi na nich stojí a jsou navržené
   správně.
4. External registration URL + veřejný list bez stavu platby.
5. Precedence overridu (2.2). Nejtěžší kus přemýšlení, nejmenší kus kódu.
6. Migrace manuální → automatický.

Pokud by se řez dělal až po bodu 3, retrofituje se do dvou čerstvě zabudovaných cest. Body 1 a 2
jsou levné a udělají zbytek bezpečnějším.
