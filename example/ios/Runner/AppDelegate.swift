import Flutter
import UIKit
// START BLOCK 1
// ALL OF THE FOLLOWING ADDED FOR LOYALTY APP
import FirebaseCore
import GoogleMaps
// This is required for calling FlutterLocalNotificationsPlugin.setPluginRegistrantCallback method.
import flutter_local_notifications
// END BLOCK1

@main
@objc class AppDelegate: FlutterAppDelegate {
  override func application(
    _ application: UIApplication,
    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
  ) -> Bool {
    //START BLOCK 2
    FirebaseApp.configure()
    GMSServices.provideAPIKey("AIthisIsAFakeIOSGoogleMapsAPIKey")

    // This is required to make any communication available in the action isolate.
    FlutterLocalNotificationsPlugin.setPluginRegistrantCallback { (registry) in
      GeneratedPluginRegistrant.register(with: registry)
    }
    
    //TMM added for flutter_local_notifications https://pub.dev/packages/flutter_local_notifications
    // and https://github.com/MaikuB/flutter_local_notifications/blob/master/flutter_local_notifications/example/ios/Runner/AppDelegate.swift
    if #available(iOS 10.0, *) {
      UNUserNotificationCenter.current().delegate = self as? UNUserNotificationCenterDelegate
    }
    // END BLOCK 2

    GeneratedPluginRegistrant.register(with: self)
    return super.application(application, didFinishLaunchingWithOptions: launchOptions)
  }
}
