/* Waybar CFFI ABI v2: album thumbnail and image-bearing GTK tooltips. */
#include <gtk/gtk.h>
#include <glib/gstdio.h>

typedef struct wbcffi_module wbcffi_module;
typedef struct {
  wbcffi_module *obj;
  const char *waybar_version;
  GtkContainer *(*get_root_widget)(wbcffi_module *);
  void (*queue_update)(wbcffi_module *);
} InitInfo;
typedef struct { const char *key; const char *value; } ConfigEntry;

const size_t wbcffi_version = 2;

typedef struct {
  GtkWidget *root, *image, *title;
  gchar *path;
  guint timer;
  gulong title_handler;
  gint64 modified;
  goffset file_size;
} AlbumArt;

static gboolean tooltip(GtkWidget *widget, gint x, gint y, gboolean keyboard,
                        GtkTooltip *tip, gpointer data) {
  (void)widget; (void)x; (void)y; (void)keyboard;
  AlbumArt *art = data;
  gchar *markup = art->title ? gtk_widget_get_tooltip_markup(art->title) : NULL;
  GdkPixbuf *cover = gdk_pixbuf_new_from_file_at_scale(art->path, 192, 192, TRUE, NULL);
  if (!cover && (!markup || !*markup)) {
    g_free(markup);
    return FALSE;
  }
  gtk_tooltip_set_markup(tip, markup && *markup ? markup : "Album artwork");
  gtk_tooltip_set_icon(tip, cover);
  g_clear_object(&cover);
  g_free(markup);
  return TRUE;
}

static GtkWidget *find_title(GtkWidget *widget) {
  if (g_strcmp0(gtk_widget_get_name(widget), "custom-now-playing") == 0)
    return widget;
  if (!GTK_IS_CONTAINER(widget)) return NULL;
  GList *children = gtk_container_get_children(GTK_CONTAINER(widget));
  GtkWidget *found = NULL;
  for (GList *child = children; child && !found; child = child->next)
    found = find_title(GTK_WIDGET(child->data));
  g_list_free(children);
  return found;
}

static gboolean refresh(gpointer data) {
  AlbumArt *art = data;
  /* The title is created after this module, so attach once the bar is built. */
  if (!art->title) {
    art->title = find_title(gtk_widget_get_toplevel(art->root));
    if (art->title) {
      g_object_add_weak_pointer(G_OBJECT(art->title), (gpointer *)&art->title);
      art->title_handler = g_signal_connect(art->title, "query-tooltip", G_CALLBACK(tooltip), art);
    }
  }
  GStatBuf info;
  if (g_stat(art->path, &info) != 0) {
    gtk_image_clear(GTK_IMAGE(art->image));
    art->modified = -1;
    return G_SOURCE_CONTINUE;
  }
  if (art->modified != info.st_mtime || art->file_size != info.st_size) {
    GdkPixbuf *cover = gdk_pixbuf_new_from_file_at_scale(art->path, 26, 26, TRUE, NULL);
    gtk_image_set_from_pixbuf(GTK_IMAGE(art->image), cover);
    g_clear_object(&cover);
    art->modified = info.st_mtime;
    art->file_size = info.st_size;
  }
  return G_SOURCE_CONTINUE;
}

void *wbcffi_init(const InitInfo *info, const ConfigEntry *entries, size_t count) {
  (void)entries; (void)count;
  AlbumArt *art = g_new0(AlbumArt, 1);
  art->root = GTK_WIDGET(info->get_root_widget(info->obj));
  art->image = gtk_image_new();
  gtk_widget_set_name(art->image, "image");
  gtk_style_context_add_class(gtk_widget_get_style_context(art->image), "album-art");
  gtk_container_add(GTK_CONTAINER(art->root), art->image);
  gtk_widget_set_has_tooltip(art->root, TRUE);
  g_signal_connect(art->root, "query-tooltip", G_CALLBACK(tooltip), art);
  art->path = g_build_filename(g_get_user_cache_dir(), "waybar", "now-playing", "cover.png", NULL);
  art->modified = -1;
  gtk_widget_show_all(art->root);
  art->timer = g_timeout_add_seconds(1, refresh, art);
  refresh(art);
  return art;
}

void wbcffi_deinit(void *instance) {
  AlbumArt *art = instance;
  g_source_remove(art->timer);
  if (art->title) {
    g_signal_handler_disconnect(art->title, art->title_handler);
    g_object_remove_weak_pointer(G_OBJECT(art->title), (gpointer *)&art->title);
  }
  g_signal_handlers_disconnect_by_data(art->root, art);
  g_free(art->path);
  g_free(art);
}
