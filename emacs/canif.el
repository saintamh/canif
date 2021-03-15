;; canif.el

;; Emacs functions for calling `canif` interactively on selected data

(defun select-from-point-to-matching-parens ()
  "Moves the mark to the matching parens. So if point is e.g. at
a closing parens, the mark is placed at the corresponding opening
parens. Basically the mark goes where the matching parens
highlight is"
  (interactive)
  (let* ((data (show-paren--default)))
    (if data
        (let* ((there-beg (nth 2 data))
               (there-end (nth 3 data)))
          (set-mark
           (if (< there-beg (point))
               there-beg
             there-end))
          (message "Mark placed at matching parens"))
      (message "No matching parens found"))))

(defun run-shell-command-replace-region (command)
  "Takes a shell command (as a string), executes with with the
contents of the region as stdin, and replaces the region with the
command's stdout."
  (let* ((stderr-buffer-name "*Shell Command STDERR*")
         (prev-stderr-buffer (get-buffer stderr-buffer-name)))
    (when prev-stderr-buffer
      (kill-buffer prev-stderr-buffer))
    (let ((coding-system-for-read 'utf-8)
          (coding-system-for-write 'utf-8))
      (shell-command-on-region
       (region-beginning)
       (region-end)
       command
       (current-buffer)
       t
       stderr-buffer-name
       t))))

(defun canif-apply-at-point (arg)
  "Applies the `canif` shell command to the structure at point.
If point is at an opening or closing bracket, the whole structure
up to the matching bracket will be pretty-printed (or, if called
with a prefix, flattened)"
  (interactive "P")
  (when (not (use-region-p))
    (select-from-point-to-matching-parens))
  (let ((command (concat "canif" (if arg " --flatten" ""))))
    (run-shell-command-replace-region command)
    ;; delete extra newline
    (exchange-point-and-mark)
    (when (looking-at "\n")
      (delete-char 1))
    (when (looking-at ",")
      (save-excursion
        (left-char)
        (when (looking-at "\n")
          (delete-char 1))))
    (exchange-point-and-mark)))
