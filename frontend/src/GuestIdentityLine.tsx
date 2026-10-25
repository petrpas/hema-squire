import { useTranslation } from "react-i18next";
import type { GuestIdentity } from "./api";

/** The one line above the registration form's first section saying who a
 *  guest is registering as, with the way back to the guest form (spec
 *  `guest-registration`, A visitor may register without an account). */
export default function GuestIdentityLine({
  identity,
  onChange,
}: {
  identity: GuestIdentity;
  onChange: () => void;
}) {
  const { t } = useTranslation();
  return (
    <p className="rail-hint guest-identity">
      {t("guest.registeringAs", { name: identity.display_name, email: identity.email })}{" "}
      <button type="button" className="link-button" onClick={onChange}>
        {t("guest.change")}
      </button>
    </p>
  );
}
