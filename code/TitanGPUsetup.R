## setup and functions

knitr::opts_chunk$set(echo = TRUE)
options(width = 150)

#suppressMessages(library(data.table))
#suppressMessages(library(tidyverse))
#suppressMessages(library(lubridate))

## Function to mark overlapping life spans in unit (sn or location). Adds two
## variables: overlap_unit and overlap_rec, marking all records in a unit and
## specific overlapping record in a unit, respectively.
mark.overlaps = function(glife, unit) {
  unit = enquo(unit) # to remove need for quoting and use !! in eval
  glife %>% 
    arrange(!! unit, insert) %>% group_by(!! unit) %>% 
    mutate(order = base::order(insert), # increasing order of inserts
           overlap_unit = 
             if_else(n() == 1,
                     FALSE,
                     any(insert[order][-1] < lag(remove[order])[-1])),
           overlap_rec = 
             if_else(rep(n() == 1, n()),
                     rep(FALSE, n()), 
                     c(FALSE, insert[order][-1] < lag(remove[order])[-1]))) %>%
    ungroup() %>% select(-order) %>% arrange(!! unit, remove)
}

## Function for plotting life (unit is sn or location) with events 
## and optionally overlaps.
plot.life_ev = function(glife, gevents, unit, file = FALSE, overlaps = TRUE,
                        outs = TRUE) {
  unit = enquo(unit) # enquoting treatment for quoteless operation
  td = as.duration(sum(glife$duration))
  if (overlaps) {
    glife = glife %>% filter(overlap_unit)
    units = unique(unlist(glife %>% select(!! unit)))
    gevents = gevents %>% filter(!! unit %in% units)
    nu = length(units)
    cat("There are", nu, "units with life overlap:\n")
    od = as.duration(sum(glife$duration[glife$overlap_rec == TRUE]))
    print(paste("Overlap life time", od, "of total life time", td,
                "(", od/td, "proportion )"))
    p = ggplot(glife, aes(x = insert, xend = remove, y = !! unit,
                          yend = !! unit, color = overlap_rec)) + 
      scale_color_manual(values=c("black", "red"))
  } else {
    p = ggplot(glife, aes(x = insert, xend = remove,
                            y = !! unit, yend = !! unit))
    units = unique(unlist(glife %>% select(!! unit)))
    nu = length(units)
  }
  
  dbe = gevents %>% filter(event == "DBE")
  otb = gevents %>% filter(event == "OTB")
  if(outs) out = glife %>% filter(out)

  p = p + geom_segment(size = 0.5) + # life lines
    geom_point(size = 0.5) # life starts
  if(outs)
    p = p + geom_point(data = out, mapping = aes(x = remove, y = !! unit),
                       color = "black", shape = "]", stroke = 1) # last seen
  p = p + geom_point(data = dbe, mapping = aes(x = remove, y = !! unit),
                     color = "red", shape = "triangle", size = 1) + # DBE
    geom_point(data = otb, mapping = aes(x = remove, y = !! unit),
               color = "blue", shape = "square", size = 1) + # OTB
    scale_x_datetime(breaks = "1 year") +
    theme_bw() + theme(axis.text.y = element_text(size = 4),
                       axis.title.x = element_blank())

  if(is.character(file)) {
    pdf(paste0(out_dir, file, ".pdf"),
      height = as.integer(nu/18 + 0.1, width = 6))
    print(p)
    dev.off()
  }
  print(p)
  invisible(p)
}

## Takes a ggplot object and prints it to a pdf file named by ggplot title with
## blanks replaced by underscores and .pdf appended. Also echoes to console 
## print by default - optional.
ggp = function(p, width = 7, height = 7, file = "gpp", echo = TRUE) {
  pdf(paste0(out_dir, file, "%03d.pdf"), width, height,
      onefile = FALSE)
  print(p)
  dev.off()
  if(echo) print(p)
}

## Titan layout plot
## Use location coordinates (need to add cage and slot?)
titan_map = function(data) {
  png("titan_xyz_trip_min.png", units="in", res=360, width=5, height=5)
    p = ggplot(xyz.trips, aes(1, z, fill=trip_min*1e6)) +
      facet_grid(y ~ x, switch="both", as.table=FALSE) +
      geom_raster() +
      scale_fill_gradient(low="red", high="blue",
                          guide = guide_colorbar(title = "microseconds",
                                                 reverse=TRUE)) +
      xlab("X") + ylab("Y") + theme_bw() +
      theme(axis.text=element_blank(), axis.ticks=element_blank(),
            panel.margin = unit(.05, "lines"),
            legend.title=element_text(angle=90),
            strip.text.x = element_text(size=8, angle=90)) +
      scale_x_continuous(breaks=NULL) +
      scale_y_continuous(breaks=seq(-0.5, 23.5, 1))
    print(p)
  dev.off()
}

diagnostic = function(sn) {
  print(gc_summary[gc_summary$sn == sn, ])
  print(gc_full[gc_full$sn == sn, ])
  print(gc_ev[gc_ev$sn == sn, ])
  print((idx = which(g_raw$sn == sn)))
  print(g_raw[idx + 0:10, ])
}
