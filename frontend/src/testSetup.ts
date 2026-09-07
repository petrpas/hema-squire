/** jsdom 26 parses `<dialog>` but implements none of its methods, so a
 *  component that opens itself with `showModal()` throws on mount. The three
 *  methods below are the part of the element the tests actually exercise:
 *  opening sets `open`, closing clears it and fires `close`. Focus, the top
 *  layer and `::backdrop` have no meaning in jsdom and are not simulated. */
if (
  typeof HTMLDialogElement !== "undefined" &&
  HTMLDialogElement.prototype.showModal === undefined
) {
  const open = function (this: HTMLDialogElement) {
    this.open = true;
  };
  HTMLDialogElement.prototype.show = open;
  HTMLDialogElement.prototype.showModal = open;
  HTMLDialogElement.prototype.close = function (this: HTMLDialogElement, returnValue?: string) {
    if (!this.open) return;
    this.open = false;
    if (returnValue !== undefined) this.returnValue = returnValue;
    this.dispatchEvent(new Event("close"));
  };
}
