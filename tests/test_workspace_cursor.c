#include "../cffi/workspace-cursor.c"

int main(int argc, char **argv) {
  gtk_init(&argc, &argv);
  GtkWidget *window = gtk_offscreen_window_new();
  GtkWidget *outer = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 0);
  GtkWidget *workspaces = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 4);
  GtkWidget *button = gtk_button_new_with_label("1");
  GtkWidget *other = gtk_button_new_with_label("Other");
  gtk_widget_set_name(workspaces, "workspaces");
  gtk_container_add(GTK_CONTAINER(window), outer);
  gtk_container_add(GTK_CONTAINER(outer), workspaces);
  gtk_container_add(GTK_CONTAINER(outer), other);
  gtk_container_add(GTK_CONTAINER(workspaces), button);
  gtk_widget_show_all(window);
  set_button_cursors(window, FALSE);
  g_assert_nonnull(gdk_window_get_cursor(gtk_button_get_event_window(GTK_BUTTON(button))));
  g_assert_null(gdk_window_get_cursor(gtk_button_get_event_window(GTK_BUTTON(other))));
  g_assert_null(gdk_window_get_cursor(gtk_widget_get_window(workspaces)));
  GtkWidget *added = gtk_button_new_with_label("2");
  gtk_container_add(GTK_CONTAINER(workspaces), added);
  gtk_widget_show_all(added);
  set_button_cursors(window, FALSE);
  g_assert_nonnull(gdk_window_get_cursor(gtk_button_get_event_window(GTK_BUTTON(added))));
  gtk_widget_destroy(window);
  g_print("Workspace buttons, gaps, unrelated buttons and new workspaces passed.\n");
  return 0;
}
