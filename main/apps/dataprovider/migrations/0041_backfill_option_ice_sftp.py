# Generated by Django 4.2.11 on 2024-06-17 08:45

from django.db import migrations


def copy_files_to_new_profiles(apps, schema_editor):
    Profile = apps.get_model('dataprovider', 'Profile')
    File = apps.get_model('dataprovider', 'File')

    profile_mappings = {
        "ICE Option Strategy": "ICE Option Strategy New",
        "ICE Option": "ICE Option New",
    }

    source_name_filter = "ICE SFTP"
    for old_profile_name, new_profile_name in profile_mappings.items():
        old_profile = Profile.objects.get(name=old_profile_name, source__name=source_name_filter)
        new_profile, _ = Profile.objects.get_or_create(name=new_profile_name, data_cut_type=old_profile.data_cut_type, source_id=old_profile.source_id, source__name=source_name_filter, target_id=old_profile.target_id)

        files_to_copy = old_profile.file_set.all()
        for file in files_to_copy:
            new_file, created = File.objects.get_or_create(
                profile=new_profile,
                file_path=file.file_path,
                defaults={
                    'data_provider': file.data_provider,
                    'source': file.source,
                    'file': file.file,
                    'status': 1  # File.FileStatus.DOWNLOADED
                }
            )
            if created:
                print(f"Copied file: {file.file_path} to new profile: {new_profile.name}")
            else:
                print(f"File: {file.file_path} already exists in the new profile: {new_profile.name}")


class Migration(migrations.Migration):
    dependencies = [
        ("dataprovider", "0040_alter_storageconfig_name"),
    ]

    operations = [
        migrations.RunPython(copy_files_to_new_profiles),
    ]
