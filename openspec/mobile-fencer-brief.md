# Brief: mobilní responzivita — šermířská část + průřezové základy

Repo: `github.com/petrpas/hema-squire`, větev z `main`.
Rozsah: **pouze šermířská část a to, co je společné celé aplikaci.** Organizátorská
konzole, Setup, Import, Export, Admin panel a Picker jsou mimo rozsah — nesahej na
ně jinak než přes průřezové změny ve skupině 1, a i tam ověř, že se konzole
nerozbila.

Než začneš implementovat, projdi to přes OpenSpec: navrhni change
(`openspec/changes/add-mobile-fencer-layout/`) s `proposal.md` a `tasks.md`
členěnými podle skupin níže. Skupiny 1 a 2 jsou závazné pořadí a musí být hotové
a odklikané dřív, než se sáhne na cokoli dalšího.

---

## Skupina 0 — pravidla, která tahle práce nemění

- `CLAUDE.md` a `openspec/squire-design-spec.md` platí beze změny. Žádné stíny,
  gradienty, radius > 2px, spinnery, shimmer, emoji, žádná saturovaná barva kromě
  `--stamp`, žádný hex mimo `tokens.css`. Mobilní verze není výmluva pro
  „materiálový" vzhled.
- **Žádné nové závislosti.** Ne Tailwind, ne CSS framework, ne knihovna na
  bottom-sheety. Vanilla CSS v `index.css`, jak je to teď.
- `index.css` má 2917 řádků a je členěný po komponentách. Mobilní pravidla patří
  **k bloku své komponenty**, ne do sekce „mobile" na konci souboru. Sekce na
  konci se do měsíce rozejde se zbytkem.
- Kde to jde, řeš to bez media query: `min()`, `clamp()`, `flex-wrap`,
  `grid-template-columns: repeat(auto-fit, minmax(...))`. Media query je až druhá
  volba, protože se váže na velikost okna, ne na velikost kontejneru, a při
  příštím refaktoru rozvržení tiše přestane sedět.

---

## Skupina 1 — průřezové základy

Tahle skupina se dotkne i organizátorské části. To je záměr; je to jediné místo,
kde se to smí stát.

### 1.1 Breakpointy

Zaveď jednu sadu a drž se jí: **480 / 768 / 1024**. 480 = telefon na výšku,
768 = tablet / telefon na šířku, 1024 = desktop.

Zapiš ji do komentáře v `tokens.css` jako kanonický seznam. **Nedávej breakpointy
do CSS proměnných** — custom properties v `@media` podmínce nefungují,
`@media (max-width: var(--bp-sm))` se tiše ignoruje a stránka vypadá, že
breakpoint neexistuje. Do media query patří literál.

### 1.2 Velikost formulářových polí — nejdůležitější jediná změna

Všechny inputy jsou dnes 14px: `.login-card input` (~ř. 228), `.param-field input`
(~ř. 880), `.modal input` (~ř. 1427), `.plea-form textarea` (~ř. 1558).

Safari na iOS **zoomne celý viewport při fokusu na jakýkoli input menší než 16px**
a nikdy sám nezoomuje zpět. Uživatel klepne na e-mail, stránka se přiblíží, zbytek
formuláře zmizí za okrajem a musí to rozštípnout prsty. Tohle samo o sobě dělá
z přihlášení nepříjemný zážitek.

Řešení: zaveď `--field-size: 16px` v `tokens.css` a použij ho ve **všech** čtyřech
blocích výše. Ne přes media query — 16px platí i na desktopu, rozdíl proti 14px je
u těchto polí opticky zanedbatelný a jedna hodnota se neroze­jde.

Alternativu `user-scalable=no` ve viewport meta **nepoužívej**, blokuje to zoom
i tam, kde ho uživatel opravdu potřebuje, a je to přístupnostní regrese.

Tohle je změna designového systému, ne jen CSS. Uprav v
`openspec/specs/design-system/spec.md` requirement *Typography conventions*: body
text zůstává 14px, ale formulářové ovládací prvky (`input`, `select`, `textarea`)
jsou nově 16px, s odůvodněním. Jinak se to při příštím auditu vrátí zpátky.

### 1.3 Výška viewportu

`.app { height: 100vh }` (~ř. 338) a `.login-page { min-height: 100vh }` (~ř. 187)
→ `100dvh`. Na mobilu se `vh` počítá k výšce bez adresního řádku, takže spodní
část stránky je pod ohybem obrazovky a topbar s kartou se nevejde.

Totéž u modálů: `max-height: 70vh` (~ř. 1407) a `88vh` (~ř. 1519) → `dvh`.

### 1.4 Bezpečné zóny

Cokoli přilepeného ke spodnímu nebo hornímu okraji potřebuje
`padding-bottom: env(safe-area-inset-bottom)` resp. `-top`, jinak to na iPhonu leží
pod indikátorem domů. Týká se to topbaru (viz 3.1) a spodní lišty modálu.

### 1.5 Dotykové cíle

Minimum 44 × 44 px pro cokoli klikatelného. Konflikt s hustotou tiskopisu je
reálný, tak ho vyřeš jednoznačně: **pod 768px se svislý padding tlačítek, tabů
a řádkových akcí zvětšuje, velikost písma a letter-spacing zůstávají.** Vzhled
zůstane úřední, jen vzdušnější. Nezvětšuj písmo, tím by se rozpadla typografická
hierarchie.

Konkrétní kandidáti: `.stage-control button/a` (padding `0.45rem 1.1rem`),
`.link-button`, `.row-action`, chipy v `.chips`.

### 1.6 Hover

`index.css` má 18 `:hover` pravidel. Na dotyku hover neexistuje a v mobilním Safari
se navíc lepí — první klepnutí uplatní hover stav, druhé teprve provede akci.

Projdi je a každé, které je čistě dekorativní (`.home-card:hover`,
`.stage-control` přechody), zabal do `@media (hover: hover)`. Každé, které je
jediným způsobem, jak se dozvědět o existenci akce, potřebuje pod 768px trvale
viditelnou variantu. Vypiš do `tasks.md`, které to jsou.

---

## Skupina 2 — přihlášení a založení účtu

**Tohle je priorita celé práce.** Přihlášení je první a často jediná věc, kterou
šermíř na telefonu udělá; když se tu zadrhne, o zbytek aplikace se nedozví.
Soubor: `frontend/src/Login.tsx`, `RequireAuth.tsx`.

### 2.1 Karta přetéká na úzkých telefonech

`.login-card { width: 22rem }` (~ř. 194) je pevných 352px, `.login-page` k tomu
přidává `padding: 2rem 1rem`. Na 360px zařízení (běžný Android) to přeteče
a stránka se dá posouvat do stran.

→ `width: min(22rem, 100%)`, a pod 480px `.login-page { padding: 1.5rem 1rem }`,
`.login-card { padding: 1.5rem 1.25rem }`.

### 2.2 Autofill — dnes nefunguje vůbec

V celém `frontend/src/` **není jediný atribut `autoComplete`.** Důsledek: iCloud
Keychain, Google Password Manager ani Bitwarden nenabídnou vyplnění a po
registraci nenabídnou uložení hesla. Šermíř tedy píše e-mail a heslo na mobilní
klávesnici ručně, pokaždé.

Doplň na přihlašovacím formuláři:

| pole | atributy |
|---|---|
| e-mail | `name="email"`, `type="email"`, `autoComplete="username"`, `autoCapitalize="none"`, `autoCorrect="off"`, `spellCheck={false}`, `inputMode="email"` |
| heslo | `name="password"`, `autoComplete="current-password"`, `enterKeyHint="go"` |

Na registračním formuláři (`SignupForm`):

| pole | atributy |
|---|---|
| e-mail | jako výše |
| heslo | `name="password"`, `autoComplete="new-password"` |
| jméno | `name="display_name"`, `autoComplete="name"`, `autoCapitalize="words"` |

`autoComplete="username"` i pro registraci — je to signál, který správcům hesel
říká „tohle je identifikátor účtu", a bez něj nenabídnou uložení dvojice.

### 2.3 Přepínání login ↔ signup

`Login.tsx` renderuje oba režimy do stejného `<form className="login-card">`.
Prohlížeč to vidí jako jeden formulář, který mění pole, a heuristika autofillu se
z toho zmate — Safari občas nabídne uložení hesla ve chvíli, kdy uživatel jen
přepnul na registraci.

→ Dej každému režimu vlastní `<form>` s vlastním stabilním `id`
(`login-form` / `signup-form`).

### 2.4 `autoFocus`

Obě pole `email` mají `autoFocus`. Na mobilu to při načtení vysune klávesnici,
což u registračního formuláře vytlačí hlavičku tiskopisu i nadpis mimo obrazovku
dřív, než si je uživatel stihne přečíst.

→ `autoFocus` jen nad 768px. Zjisti šířku jednou při mountu
(`window.matchMedia("(min-width: 768px)").matches`), ne v render cyklu.

### 2.5 Vypršelý token — nejhorší návratový scénář

`RequireAuth.tsx` inicializuje `authed` pouhou přítomností tokenu v localStorage
a selhání `api.account()` polyká prázdným handlerem `() => {}`.

Na mobilu je token typicky týdny starý. Uživatel otevře záložku, dostane
přihlášený shell s prázdným jménem v identity bloku a prázdným seznamem turnajů —
ne přihlašovací formulář. Vypadá to jako rozbitá aplikace, ne jako odhlášení.

→ Když `api.account()` vrátí 401, zavolej `setToken(null)` a přepni na `Login`.
Ostatní chyby (síť) nech být — offline uživatel nemá být odhlášen. Zachovej
chování `RequireAuth`, že se `Login` renderuje na původní URL, aby cíl přežil
přihlášení.

### 2.6 Stav odesílání

Tlačítko se při `busy` jen zablokuje, text se nemění. Na mobilní síti je mezi
klepnutím a odpovědí klidně dvě vteřiny bez jakékoli zpětné vazby a uživatel
klepne znovu.

Spinner design zakazuje, takže: **změň popisek tlačítka** na průběhovou variantu
(`login.submitting` / `signup.submitting`, česky i anglicky). Statický text, žádná
animace — vejde se to do pravidel.

### 2.7 Chybová hláška neposouvá rozvržení

`.login-error` se vkládá nad tlačítko, takže když se objeví, tlačítko skočí dolů.
Na dotyku to znamená, že klepnutí těsně po chybě mine.

→ Rezervuj místo pod polem hesla (`min-height` odpovídající jednomu řádku), nebo
hlášku umísti tak, aby tlačítko zůstalo na svém místě.

### 2.8 HR vyhledávač uvnitř registrace

`SignupForm` renderuje `HRSearchPicker` inline doprostřed formuláře. Na 390px se
formulář natáhne na tři obrazovky a uprostřed má vyhledávací pole s výsledky —
uživatel ztratí kontext, co vlastně vyplňoval.

→ Pod 768px z toho udělej samostatný krok přes celou obrazovku: „Najít profil na
HEMA Ratings" překryje formulář, potvrzení kandidáta se vrátí zpět a doplní jméno.
Stav formuláře musí přežít (drž ho ve stejné komponentě, nepřepínej route).
Nad 768px zůstává inline chování beze změny.

---

## Skupina 3 — shell a navigace šermíře

### 3.1 Topbar

`FencerShell.tsx` skládá do jednoho flex řádku s `gap: 2rem`: logo, `.stage-control`
se čtyřmi taby, identity blok se jménem a HR ID, a `AccountMenu`. To je zhruba
600px obsahu; na 390px se to nevejde ani omylem.

Pod 768px:

- **První řádek:** logo vlevo, `AccountMenu` vpravo. Identity blok se do menu
  sbalí — jméno a HR ID se ukážou až po otevření, ne trvale v liště.
- **Druhý řádek:** taby přes celou šířku, vodorovně scrollovatelné
  (`overflow-x: auto`, `scroll-snap-type: x proximity`, skrytý scrollbar). Dělicí
  1px linky mezi taby a rámeček `.stage-control` zůstávají — je to pruh z tiskopisu,
  ne pilulky.
- Aktivní tab musí být po načtení viditelný: `scrollIntoView({ inline: "center" })`
  při změně tabu. Bez toho uživatel na tabu „Moje" nevidí, že je vybraný.
- Topbar `position: sticky; top: 0`, **ne `fixed`** — fixed se v mobilním Safari
  při skrývání adresního řádku trhá.

`.stage-control` má `flex-shrink: 0`; to je uvnitř scroll kontejneru správně, nech to.

### 3.2 Workspace odsazení

`.home-workspace` i `.detail-workspace` mají `padding: 1.5rem`. Na 390px to ubere
48px z 390, tedy 12 % šířky na prázdno.

→ Pod 480px `padding: 1rem 0.75rem`. `max-width: 44rem` na potomcích může zůstat,
jen ověř, že `.home-card` s `padding: 1rem 1em` nevytváří dvojité odsazení.

---

## Skupina 4 — Fencer Home

Dobrá zpráva: `FencerHome.tsx` už je kartový seznam (`.home-list` / `.home-card`),
ne tabulka. Většina práce tady odpadá.

- `.home-card-header` je `justify-content: space-between` s logem a nadpisem →
  přidej `flex-wrap: wrap`. Nadpis v `--font-doc` 16px se na úzké obrazovce jinak
  smrskne do dvou znaků na řádek vedle loga.
- `.home-card-logo` má pevných 88px. Pod 480px zmenši na 56px, nebo ho úplně
  vynech — na kartě v seznamu na telefonu nenese informaci.
- `.chips` s disciplínami: ověř `flex-wrap` a to, že řádek chipů nepřeteče.
  Při víc než čtyřech disciplínách zvaž pod 480px zkrácení na první tři + počet
  zbytku.
- `.home-card-when` a `.home-card-organizers` — zkontroluj, že se dlouhá jména
  pořadatelů zalamují (`overflow-wrap: anywhere` na dlouhých řetězcích bez mezer).

## Skupina 5 — Detail turnaje

- `.detail-header` je flex řádek: `h1` (serif, `flex: 1`), `.stage-control`
  se třemi taby a zavírací `.row-action`. Na 390px se to nevejde.
  → Pod 768px: nadpis na vlastní řádek, taby pod ním přes celou šířku stejným
  scroll pruhem jako v 3.1. Zavírací akce zůstává v úrovni nadpisu vpravo.
- `.amount-line` je `grid-template-columns: 1fr auto` — to drží i na úzké
  obrazovce, nech být. Jen ověř, že dlouhé české popisky položek
  (`amount-label`) nepřetlačí částku; `min-width: 0` na první sloupec.
- `.detail-description` je organizátorem psaný markdown přes `Prose.tsx`.
  Zkontroluj, co dělá s obrázky a tabulkami v markdownu: `img { max-width: 100% }`
  a wrapper s `overflow-x: auto` kolem `table` uvnitř `.prose`. Pořadatelé tam
  budou lepit cokoli.
- `.modal-actions` v potvrzovacích dialozích: pod 480px tlačítka pod sebe, na plnou
  šířku, destruktivní akce dole (těžší se na ni omylem trefit palcem).
- Modály obecně (`~ř. 1519`, `width: 46rem`): pod 768px `width: 100%`,
  `max-height: 100dvh`, bez zaobleného rámu odsazeného od okraje — na telefonu je
  to celá obrazovka.

## Skupina 6 — platební útržek

`PaymentPanel.tsx`. Tady je jediná věcná, ne jen vizuální vada mobilní verze.

### 6.1 QR kód na vlastní obrazovce nenaskenuješ

Celý flow s SPAYD QR předpokládá „platba na monitoru, telefon v ruce". Na mobilu
je uživatel na tomtéž zařízení a QR kód je mu k ničemu. Dnes nemá žádnou
alternativu — číslo účtu ani VS se nedají zkopírovat, jsou to jen `<strong>`
elementy.

Pod 768px doplň:

- **Tlačítko „Uložit QR do galerie"** — `qr_png_base64` ulož jako soubor přes
  `<a download>` s data URL. Všechny velké české bankovní aplikace (George, Fio,
  Air Bank, Revolut, KB) umí načíst QR platbu z obrázku v galerii. Tohle je
  nejrychlejší cesta k zaplacení a měla by být první.
- **Kopírovací akce u čísla účtu, IBAN, VS a částky.** `navigator.clipboard.writeText`
  (funguje jen přes HTTPS — v produkci na hemasquire.eu ano, v dev přes
  `localhost` taky; přes IP v LAN ne, počítej s tím při testování).
  Potvrzení kopírování řeš staticky podle designu: krátká textová poznámka
  u pole, žádný animovaný toast.
- Tyhle akce dej i na desktop. Kopírovat VS myší je otravné všude.

### 6.2 Rozvržení útržku

`.payment-block` je `flex-direction: row` s `.param-fields` vlevo a `.payment-qr`
o pevných `10rem` (160px) vpravo. Na 390px zbude na pole 160px.

→ Pod 480px `flex-direction: column`, QR nahoru, vycentrovaný, `width: min(10rem, 60%)`.
Pod ním akce z 6.1, pod nimi pole. Pořadí podle toho, co uživatel skutečně
potřebuje první.

### 6.3 EUR taby

`.payment-slip-heading` je `space-between` s nadpisem a `.stage-control`. Se dvěma
taby (CZK / EUR) to na 390px projde, ale ověř to s delším názvem měny; případně
nadpis a taby pod sebe.

## Skupina 7 — profil

`ProfilePage.tsx` — projdi stejnou logikou: `.param-fields` mřížky na jeden
sloupec, HR vyhledávač jako celoobrazovkový krok (stejná komponenta jako v 2.8,
ne druhá implementace), formulářová pole 16px ze skupiny 1.

---

## Ověření

- `npm run lint` (`tsc -b --noEmit`) a `npm run build` musí projít.
- **Poznámka:** `openspec/changes/add-payments-console-ui/proposal.md` tvrdí, že
  frontend nemá test runner. To už neplatí — `package.json` má
  `"test": "vitest run"` a v `src/` je šest `.test.tsx` souborů. Při psaní
  proposalu vycházej z `package.json`, ne z toho tvrzení, a zmiň jeho opravu.
- Nepřidávej Playwright kvůli téhle práci; je to nová závislost a vizuální
  regrese na třech šířkách se jí stejně spolehlivě nechytí.
- Ruční průchod v DevTools na **360 / 390 / 768 / 1024 px**, pro každou šířku:
  přihlášení → registrace účtu → home → detail turnaje → registrace na turnaj →
  platební útržek → profil → odhlášení.
- **Na skutečném iPhonu ověř zvlášť:** zoom při fokusu na input (skupina 1.2),
  nabídku autofillu a uložení hesla (2.2, 2.3), chování topbaru při scrollu (3.1)
  a načtení QR do bankovní aplikace z galerie (6.1). Ani jedno z toho DevTools
  neemuluje věrně.
- Průřezová kontrola: otevři organizátorskou konzoli na desktopu a ověř, že ji
  skupina 1 nerozbila — zvlášť 16px pole v `EditableCell` a hustotu tabulek.

## Mimo rozsah

Nedělej v této změně: PWA, service worker, offline režim, mobilní verzi konzole,
bottom navigation, jakoukoli změnu barev nebo typografické škály nad rámec bodu
1.2, a jakýkoli zásah do backendu.
