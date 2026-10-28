/* Run in a graphical session; uses an offscreen window, never opens a bar. */
#include "../cffi/album-art.c"

static GtkContainer *root_widget(wbcffi_module *obj) { return GTK_CONTAINER(obj); }

int main(int argc, char **argv) {
  gchar *cache = g_dir_make_tmp("waybar-tooltip-test-XXXXXX", NULL);
  g_setenv("XDG_CACHE_HOME", cache, TRUE);
  gtk_init(&argc, &argv);
  GtkWidget *window = gtk_offscreen_window_new();
  GtkWidget *box = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 0);
  GtkWidget *root = gtk_event_box_new();
  GtkWidget *title = gtk_label_new("Track");
  gtk_widget_set_name(title, "custom-now-playing");
  gtk_widget_set_tooltip_markup(title, "Track\nArtist");
  gtk_container_add(GTK_CONTAINER(window), box);
  gtk_container_add(GTK_CONTAINER(box), root);
  gtk_container_add(GTK_CONTAINER(box), title);
  InitInfo info = {.obj = (wbcffi_module *)root, .get_root_widget = root_widget};
  AlbumArt *art = wbcffi_init(&info, NULL, 0);
  g_assert_true(art->title == title);
  gchar *directory = g_path_get_dirname(art->path);
  g_mkdir_with_parents(directory, 0700);
  GdkPixbuf *cover = gdk_pixbuf_new(GDK_COLORSPACE_RGB, FALSE, 8, 256, 256);
  gdk_pixbuf_fill(cover, 0x308c49ff);
  g_assert_true(gdk_pixbuf_save(cover, art->path, "png", NULL, NULL));
  g_object_unref(cover);
  refresh(art);
  g_assert_cmpint(gtk_image_get_storage_type(GTK_IMAGE(art->image)), ==, GTK_IMAGE_PIXBUF);
  GtkTooltip *tip = g_object_new(GTK_TYPE_TOOLTIP, NULL);
  gboolean handled = FALSE;
  g_signal_emit_by_name(title, "query-tooltip", 0, 0, FALSE, tip, &handled);
  g_assert_true(handled);
  g_assert_true(tooltip(root, 0, 0, FALSE, tip, art));
  g_unlink(art->path);
  refresh(art);
  g_assert_cmpint(gtk_image_get_storage_type(GTK_IMAGE(art->image)), ==, GTK_IMAGE_EMPTY);
  g_assert_true(tooltip(root, 0, 0, FALSE, tip, art)); /* Text-only fallback. */
  gtk_widget_destroy(title);
  g_assert_null(art->title);
  g_assert_false(tooltip(root, 0, 0, FALSE, tip, art));
  g_object_unref(tip);
  wbcffi_deinit(art);
  gtk_widget_destroy(window);
  g_rmdir(directory);
  gchar *parent = g_path_get_dirname(directory);
  g_rmdir(parent);
  g_rmdir(cache);
  g_free(parent); g_free(directory); g_free(cache);
  g_print("Album-art tooltip, title hook, missing-art fallback and cleanup passed.\n");
  return 0;
}
