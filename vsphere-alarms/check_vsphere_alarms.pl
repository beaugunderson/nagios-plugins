#!/usr/bin/perl -w

use strict;
use warnings;

use Term::ANSIColor;

use VMware::VILib;
use VMware::VIRuntime;

$SIG{__DIE__} = sub{Util::disconnect()};

Opts::parse();
Opts::validate();

Util::connect();

my $sc = Vim::get_service_content();

listAlarms($sc);

Util::disconnect();

sub alarmsForEntity {
   my ($entity, $alarmManager) = @_;

   my $alarmStates = $alarmManager->GetAlarmState(entity => $entity);

   foreach(@$alarmStates) {
      my $alarm_reference = $_->alarm;
      my $alarm = Vim::get_view(mo_ref => $alarm_reference);

      if($alarm->info->enabled) {
         if($_->overallStatus->val eq "red" ||
            $_->overallStatus->val eq "yellow") {
            my $alarm_key = $_->key;
            my $alarm_state = $_->overallStatus->val;
            my $alarm_name = $alarm->info->name;
            my $alarm_entity = $entity->name;

            printf '{"key":"%s","state":"%s","name":"%s","entity":"%s"},', $alarm_key, $alarm_state, $alarm_name, $alarm_entity;
         }
      }

      if($@) {
         print "Error in getAlarmState: " . $@ . "\n";
      }
   }
}

sub listAlarms {
   my ($sc) = @_;

   my @view_types = ("ClusterComputeResource", "ComputeResource", "Datacenter", "Folder", "HostSystem", "ResourcePool", "VirtualMachine");

   my $alarmManager = Vim::get_view(mo_ref => $sc->alarmManager);

   print "[";

   foreach(@view_types) {
      my $view = Vim::find_entity_views(view_type => $_);

      foreach(@$view) {
         alarmsForEntity($_, $alarmManager);
      }
   }

   print "]\n";
}
