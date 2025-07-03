PROJECT_DIR="$HOME/Documents/uni-semester-projects/bde/project/"
TMUX_SESSION_NAME="project"
TMUX_WINDOW_NAME="dev"
TMUX_WINDOW_NAME2="test"

if ! tmux has-session -t "$TMUX_SESSION_NAME" 2>/dev/null; then
  echo "Creating new tmux session: $TMUX_SESSION_NAME"
  tmux new-session -s "$TMUX_SESSION_NAME" -n "$TMUX_WINDOW_NAME" -d
else
  echo "Session $TMUX_SESSION_NAME already exists. Attaching to it."
fi

if tmux list-windows -t "$TMUX_SESSION_NAME" -F '#{window_name}' | grep -q "^$TMUX_WINDOW_NAME2$"; then
  echo "Window '$TMUX_WINDOW_NAME2' already exists in session '$TMUX_SESSION_NAME'"
else
  echo "Creating new window '$TMUX_WINDOW_NAME2' in session '$TMUX_SESSION_NAME'."
  tmux new-window -t "$TMUX_SESSION_NAME" -n "$TMUX_WINDOW_NAME2"
fi
echo "Sending keys to tmux"
tmux send-keys -t "$TMUX_SESSION_NAME:$TMUX_WINDOW_NAME.0" "cd $PROJECT_DIR" Enter
tmux send-keys -t "$TMUX_SESSION_NAME:$TMUX_WINDOW_NAME.0" "nvim" Enter
echo 'Moved into project directory and ready!'
tmux send-keys -t "$TMUX_SESSION_NAME:$TMUX_WINDOW_NAME2.0" "cd $PROJECT_DIR" Enter
echo 'Create test window and prepare environment for testing'
tmux send-keys -t "$TMUX_SESSION_NAME:$TMUX_WINDOW_NAME2.0" "export PIPENV_IGNORE_VIRTUALENVS=1 && pipenv shell" Enter
echo 'Moved into project directory and ready!'
echo "Commands sent. Attaching to session (Ctrl+b d to detach)."
tmux attach-session -t "$TMUX_SESSION_NAME"
