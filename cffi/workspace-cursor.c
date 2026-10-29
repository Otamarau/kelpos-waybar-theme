/* Waybar CFFI ABI v2: set cursors on GTK button input windows. */
#include <gtk/gtk.h>

typedef struct wbcffi_module wbcffi_module;
typedef struct {
  wbcffi_module *obj;
  const char *waybar_version;
  GtkContainer *(*get_root_widget)(wbcffi_module *);
  void (*queue_update)(wbcffi_module *);
} InitInfo;
typedef struct { const char *key; const char *value; } ConfigEntry;
const size_t wbcffi_version = 2;

typedef struct { GtkWidget *root; guint timer; } WorkspaceCursor;

static void set_button_cursors(GtkWidget *widget, gboolean in_workspaces) {
  in_workspaces |= g_strcmp0(gtk_widget_get_name(widget), "workspaces") == 0;
  if (in_workspaces && GTK_IS_BUTTON(widget)) {
    GdkWindow *window = gtk_button_get_event_window(GTK_BUTTON(widget));
    if (window && !g_object_get_data(G_OBJECT(window), "workspace-pointer")) {
      GdkCursor *cursor = gdk_cursor_new_from_name(gdk_window_get_display(window), "pointer");
      gdk_window_set_cursor(window, cursor);
      g_clear_object(&cursor);
      g_object_set_data(G_OBJECT(window), "workspace-pointer", GINT_TO_POINTER(1));
    }
  }
  if (GTK_IS_CONTAINER(widget)) {
    GList *children = gtk_container_get_children(GTK_CONTAINER(widget));
    for (GList *child = children; child; child = child->next)
      set_button_cursors(GTK_WIDGET(child->data), in_workspaces);
    g_list_free(children);
  }
}

static gboolean refresh(gpointer data) {
  WorkspaceCursor *state = data;
  /* Also catch workspaces created after startup, on each output. */
  set_button_cursors(gtk_widget_get_toplevel(state->root), FALSE);
  return G_SOURCE_CONTINUE;
}

void *wbcffi_init(const InitInfo *info, const ConfigEntry *entries, size_t count) {
  (void)entries; (void)count;
  WorkspaceCursor *state = g_new0(WorkspaceCursor, 1);
  state->root = GTK_WIDGET(info->get_root_widget(info->obj));
  gtk_widget_set_no_show_all(state->root, TRUE);
  gtk_widget_hide(state->root);
  state->timer = g_timeout_add(100, refresh, state);
  return state;
}

void wbcffi_deinit(void *instance) {
  WorkspaceCursor *state = instance;
  g_source_remove(state->timer);
  g_free(state);
}
