import 'package:flutter/material.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Brand Demo',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepPurple),
      ),
      home: const BrandHomePage(),
    );
  }
}

class BrandHomePage extends StatelessWidget {
  const BrandHomePage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: const Color(0xFF2255CC), //BRANDCOLOR
        title: const Text('Globex Industries Brand Demo'), //BRANDNAME
      ),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              // Brand logo from assets — this image changes when you switch brands
              Image.asset(
                'assets/images/brand/logo_wide.png',
                width: 320,
                fit: BoxFit.contain,
              ),
              const SizedBox(height: 32),
              // Brand app icon
              Image.asset(
                'assets/images/brand/appicon_square.png',
                width: 128,
                height: 128,
                fit: BoxFit.contain,
              ),
              const SizedBox(height: 32),
              Text(
                'Switch brands using flutter_app_transmuter\n'
                'Run each version and see that each has its own assets, splash screens, and app icon!'
                '\nEssentially anything can be changed per brand.',

                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodyLarge,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
